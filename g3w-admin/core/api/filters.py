# coding=utf-8
""""Filters for QGIS feature requests

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the Mozilla Public License 2.0.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2020-02-10'
__copyright__ = 'Copyright 2020, Gis3w'

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsRectangle,
    QgsCoordinateTransformContext,
)
from rest_framework.exceptions import ParseError


class BaseFilterBackend():
    """Base class for QGIS request filters"""

    def apply_filter(self, request, qgis_layer, qgis_feature_request, view=None):
        """Apply the filter to the QGIS feature request

        :param request: Django request
        :type request: HttRequest
        :param qgis_layer: QGIS vector layer
        :type qgis_layer: QgsVectorLayer
        :param qgis_feature_request: QGIS feature request
        :type qgis_feature_request: QgsFeatureRequest
        :param view: Django view, optional
        :type view: optional, Django view
        :raises NotImplementedError: all subclasses must implement this method
        """

        raise NotImplementedError("All subclasses must implement this method")

    def _is_valid_field(self, qgis_layer, field_name, view=None):
        """Checks if the field name belongs to the layer and if it's not to be excluded from WFS/WMS

        :param qgis_layer: layer
        :type qgis_layer: QgsVectorLayer
        :param field_name: field name
        :type field_name: str
        :param view: the Django caller view, defaults to None
        :type view: Django view, optional
        """

        exclude_fields = []

        if view is not None and view.layer.exclude_attribute_wms:
            exclude_fields = eval(view.layer.exclude_attribute_wms)

        return field_name not in exclude_fields and field_name in qgis_layer.fields().names()

    def _quote_identifier(self, identifier):
        """Returns a quoted identifier enclosed by double quotes"""

        return '"%s"' % identifier.replace('"', '\\"')

    def _quote_value(self, identifier):
        """Returns a quoted value enclosed by single quotes"""

        return "'%s'" % identifier.replace('\'', '\\\'')


class SearchFilter(BaseFilterBackend):
    """A filter backend that does an ILIKE string search in all fields"""

    def apply_filter(self, request, qgis_layer, qgis_feature_request, view=None):

        if request.query_params.get('search'):

            search_parts = []

            for search_term in request.query_params.get('search').split(','):

                search_term = self._quote_value('%' + search_term + '%')
                exp_template = '{field_name} ILIKE ' + search_term
                exp_parts = []

                for f in qgis_layer.fields():

                    if not self._is_valid_field(qgis_layer, f.name(), view):
                        continue
                    exp_parts.append(exp_template.format(
                        field_name=self._quote_identifier(f.name())))

                if exp_parts:
                    search_parts.append(' OR '.join(exp_parts))

            if search_parts:

                search_expression = '(' + ' AND '.join(search_parts) + ')'
                current_expression = qgis_feature_request.filterExpression()

                if current_expression:
                    search_expression = '( %s ) AND ( %s )' % (
                        current_expression, search_expression)

                qgis_feature_request.setFilterExpression(search_expression)


class OrderingFilter(BaseFilterBackend):
    """A filter backend that defines ordering"""

    def apply_filter(self, request, qgis_layer, qgis_feature_request, view=None):

        if request.query_params.get('ordering') is not None:

            ordering_rules = []

            for ordering in request.query_params.get('ordering').split(','):
                ascending = True
                if ordering.startswith('-'):
                    ordering = ordering[1:]
                    ascending = False

                if not self._is_valid_field(qgis_layer, ordering, view):
                    continue

                ordering_rules.append(QgsFeatureRequest.OrderByClause(
                   ordering, ascending))

            if ordering_rules:
                order_by = QgsFeatureRequest.OrderBy(ordering_rules)
                qgis_feature_request.setOrderBy(order_by)


class IntersectsBBoxFilter(BaseFilterBackend):

    def _get_filter_bbox(self, request):
        """Creates a QgsRectangle from the BBOX request

        :param request: request
        :type request: django request
        :raises ParseError: parse error
        :return: bbox rectangle
        :rtype: QgsRectangle
        """

        if request.method == 'POST':
            request_data = request.data
        else:
            request_data = request.query_params
        bbox_string = request_data.get('bbox_param', None)
        if not bbox_string:
            return None

        try:
            p1x, p1y, p2x, p2y = (float(n) for n in bbox_string.split(','))
        except ValueError:
            raise ParseError('Invalid bbox string supplied for parameter bbox_param')

        return QgsRectangle(p1x, p1y, p2x, p2y)

    def apply_filter(self, request, qgis_layer, qgis_feature_request, view=None):

        bbox_filter = self._get_filter_bbox(request)

        if bbox_filter:

            include_overlapping = getattr(
                view, 'bbox_filter_include_overlapping', True)

            if not include_overlapping:
                # FIXME: IntersectsBBoxFilter within operator
                raise NotImplementedError('IntersectsBBoxFilter within operator not yet implemented')

            if hasattr(view, 'reproject') and view.reproject:
                from_srid = view.layer.project.group.srid.auth_srid
                to_srid = view.layer.srid
                ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(
                    from_srid), QgsCoordinateReferenceSystem(to_srid), QgsCoordinateTransformContext())
                bbox_filter = ct.transform(bbox_filter)

            qgis_feature_request.setFilterRect(bbox_filter)


class CentroidBBoxFilter(IntersectsBBoxFilter):
    # FIXME: untested

    def __init__(self, **kwargs):

        self.tolerance = kwargs['tolerance'] if 'tolerance' in kwargs else 10
        super(CentroidBBoxFilter, self).__init__(**kwargs)

    def _get_filter_bbox(self, request):

        tolerance = request.query_params.get('tolerance', '10')
        polygon = super()._get_filter_bbox(request)
        return polygon.buffered(float(tolerance))


class SuggestFilterBackend(BaseFilterBackend):
    """Backend filter that returns ILIKE matches for a field|value tuple"""

    def apply_filter(self, request, qgis_layer, qgis_feature_request, view=None):

        suggest_value = request.query_params.get('suggest')

        if suggest_value:

            # get field and value
            field_name, field_value = suggest_value.split('|')

            if field_name and field_value and self._is_valid_field(qgis_layer, field_name):

                search_expression = '{field_name} ILIKE {field_value}'.format(
                    field_name=self._quote_identifier(field_name),
                    field_value=self._quote_value('%' + field_value + '%')
                    )

                current_expression = qgis_feature_request.filterExpression()

                if current_expression:
                    search_expression = '( %s ) AND ( %s )' % (
                        current_expression, search_expression)

                qgis_feature_request.setFilterExpression(search_expression)

