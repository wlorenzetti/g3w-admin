""""Constraints module models

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the Mozilla Public License 2.0.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2019-07-19'
__copyright__ = 'Copyright 2019, Gis3w'


import logging

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from qgis.core import (
    QgsFeatureRequest,
    QgsMultiPolygon,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsGeometry,
    QgsExpression,
)

from core.utils.models import get_creator_from_qdjango_layer
from core.utils.qgisapi import get_qgis_features, get_qgis_layer
from qdjango.models import Layer


logger = logging.getLogger(__name__)


class Constraint(models.Model):
    """Main Constraint class. Links together two layers: the editing layer and the constraint layer.
    """

    active = models.BooleanField(default=True)
    editing_layer = models.ForeignKey(
        Layer, on_delete=models.CASCADE, related_name='editing_layer')
    constraint_layer = models.ForeignKey(
        Layer, on_delete=models.CASCADE, related_name='constraint_layer')

    @property
    def editing_layer_qgs_layer_id(self):
        """Return the QGIS layer id for editing layer"""

        return self.editing_layer.qgs_layer_id

    @property
    def constraint_layer_qgs_layer_id(self):
        """Return the QGIS layer id for constraint layer"""

        return self.constraint_layer.qgs_layer_id

    @property
    def constraint_layer_name(self):
        """Return the QGIS layer name for constraint layer"""

        return self.constraint_layer.name

    @property
    def constraint_rule_count(self):
        """Return the rules count for constraint"""

        return self.constraintrule_set.count()

    def clean(self):
        """Make sure the layer is either PG or SL and check that constraint layer is Polygon"""

        if self.editing_layer.layer_type not in ('spatialite', 'postgres') or self.constraint_layer.layer_type not in ('spatialite', 'postgres'):
            raise ValidationError(
                _('Layers types must be spatialite or postgres'))

        if 'Polygon' not in self.constraint_layer.geometrytype:
            raise ValidationError(
                _('Constraint layer geometry type must be Polygon or MultiPolygon'))

        if self.editing_layer.pk == self.constraint_layer.pk:
            raise ValidationError(
                _('Editing and constraints layer cannot be the same layer'))

    def __str__(self):
        return "%s, %s" % (self.editing_layer, self.constraint_layer)

    class Meta:
        managed = True
        verbose_name = _('Layer constraint')
        verbose_name_plural = _('Layer constraints')
        app_label = 'editing'


class ConstraintRule(models.Model):
    """Constraint rule class: links the constraint with a user or a group and
    defines the constraint SQL rule"""

    constraint = models.ForeignKey(Constraint, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True)
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, blank=True, null=True)
    rule = models.TextField(
        _("SQL WHERE clause for the constraint layer"), max_length=255)

    @property
    def active(self):
        """The rule is active if the constraint is"""

        return self.constraint.active

    def __str__(self):
        return "%s, %s: %s" % (self.constraint, self.user_or_group, self.rule)

    class Meta:
        managed = True
        verbose_name = _('Constraint rule')
        verbose_name_plural = _('Constraint rules')
        unique_together = (('constraint', 'user', 'rule'),
                           ('constraint', 'group', 'rule'))
        app_label = 'editing'

    @property
    def user_or_group(self):
        """Returns the user or the group for this constraint"""

        if self.user:
            return self.user
        return self.group

    def clean(self):
        """Make sure either a group or a user are defined and that the SQL query runs without errors"""

        if self.group and self.user:
            raise ValidationError(
                _('You cannot define a user and a group at the same time'))

        if not self.group and not self.user:
            raise ValidationError(
                _('You must define a user OR a group'))

        sql_valid, ex = self.validate_sql()
        if not sql_valid:
            raise ValidationError(
                _('There is an error in the SQL rule where condition: %s' % ex))

    def get_constraint_geometry(self):
        """Returns the geometry from the constraint layer and rule

        :return: the constraint geometry and the number of matched records
        :rtype: tuple( MultiPolygon, integer)
        """

        constraint_layer = get_qgis_layer(self.constraint.constraint_layer)
        editing_layer = get_qgis_layer(self.constraint.editing_layer)

        # Get the geometries from constraint layer and rule
        qgis_feature_request = QgsFeatureRequest()
        qgis_feature_request.setFilterExpression(self.rule)

        features = get_qgis_features(constraint_layer, qgis_feature_request, exclude_fields='__all__')

        if not features:
            return '', 0

        geometry = QgsMultiPolygon()

        for feature in features:
            geom = feature.geometry().constGet()
            geometry.insertGeometry(geom.clone(), 0)

        # Now, transform into a GEOS geometry
        if constraint_layer.crs() != editing_layer.crs():
            ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(constraint_layer.crs()), QgsCoordinateReferenceSystem(editing_layer.crs()), QgsCoordinateTransformContext())
            geometry.transform(ct)

        constraint_geometry = MultiPolygon.from_ewkt('SRID=%s;' % editing_layer.crs().postgisSrid() +geometry.asWkt())

        return constraint_geometry, constraint_geometry.num_geom

    # FIXME: Remove this method
    def _____get_filters(self):
        """Construct the filters for the query set

        :return: filters for the query set
        :rtype: dict
        """

        editing_model_creator = get_creator_from_qdjango_layer(
            self.constraint.editing_layer)
        editing_geom_field = [k for k, v in editing_model_creator.django_model_fields.items(
        ) if isinstance(v, GeometryField)][0]

        constraint_geometry, matched_counter = self.get_constraint_geometry()

        # set spatial predicate for validation
        spatial_predicate = getattr(
            settings, 'EDITING_CONSTRAINT_SPATIAL_PREDICATE', 'contains')
        if spatial_predicate == 'contains':
            spatial_predicate = 'within'

        # Now fetch data from editing layer
        # TODO: check if we want "intersects" instead
        filter_key = editing_geom_field + '__' + spatial_predicate
        filters = {
            filter_key: constraint_geometry
        }
        return filters

    def apply_filter(self, request, qgis_feature_request, view):
        """Apply the rule filters to the feature request

        :param request: incoming request
        :type request: Django request
        :param qgis_feature_request: QGIS feature request
        :type qgis_feature_request: QgsFeatureRequest
        """

        constraint_geometry, __ = self.get_constraint_geometry()

        if constraint_geometry:
            expression = ''
            spatial_predicate = getattr(
            settings, 'EDITING_CONSTRAINT_SPATIAL_PREDICATE', 'contains')
            if spatial_predicate == 'contains':
                # The constraint geometry contains feature geometry
                expression = "contains(geom_from_wkt( '{wkt}' ), $geometry )".format(wkt=constraint_geometry.wkt)
            else:
                # The constraint geometry is within the feature geometry
                expression = "within(geom_from_wkt( '{wkt}' ), $geometry)".format(wkt=constraint_geometry.wkt)

            current_expression = qgis_feature_request.filterExpression()

            if current_expression:
                expression = '( %s ) AND ( %s )' % (current_expression, expression)

            qgis_feature_request.setFilterExpression(expression)



    # FIXME: remove this method
    def _____get_query_set(self):
        """Returns the query set from the editing layer filtered by the rule"""

        filters = self.get_filters()
        constraint_geometry = list(filters.values())[0]
        editing_model_creator = get_creator_from_qdjango_layer(
            self.constraint.editing_layer)
        # Apparently, in spatialite:
        # select st_within(st_geomfromtext('point( 9 9)'), st_geomfromtext('multipolygon empty'));
        # returns -1 that is interpreted as TRUE, so we invert the filter to return an empty query set
        # if constraint_geometry.empty and self.constraint.editing_layer.layer_type == 'spatialite':
        #    return editing_model_creator.geo_model.objects.exclude(**filters)
        # else:
        return editing_model_creator.geo_model.objects.filter(**filters)

    def validate_sql(self):
        """Checks if the rule can be executed without errors

        :return: (True, None) if rule has valid SQL, (False, ValidationError) if it is not valid
        :rtype: tuple (bool, ValidationError)
        """

        try:
            req = QgsFeatureRequest()
            self.apply_filter(None, req, None)
            expression = req.filterExpression()
            if expression is None:
                return False, QgsExpression(self.rule).parserErrorString()
            if not expression.isValid():
                return False, expression.parserErrorString()
        except Exception as ex:
            logger.debug('Validate SQL failed: %s' % ex)
            return False, ex
        return True, None

    @classmethod
    def get_constraints_for_user(cls, user, editing_layer):
        """Fetch the constraints for a given user and editing layer

        :param user: the user
        :type user: User
        :param layer: the editing layer
        :type layer: Layer
        :return: a list of ConstraintRule
        :rtype: QuerySet
        """

        constraints = Constraint.objects.filter(editing_layer=editing_layer)
        if not constraints:
            return []
        user_groups = user.groups.all()
        if user_groups.count():
            return cls.objects.filter(Q(constraint__in=constraints), Q(user=user) | Q(group__in=user_groups))
        else:
            return cls.objects.filter(constraint__in=constraints, user=user)

    @classmethod
    def get_active_constraints_for_user(cls, user, editing_layer):
        """Fetch the active constraints for a given user and editing layer

        :param user: the user
        :type user: User
        :param layer: the editing layer
        :type layer: Layer
        :return: a list of ConstraintRule
        :rtype: QuerySet
        """

        constraints = Constraint.objects.filter(
            editing_layer=editing_layer, active=True)
        if not constraints:
            return []
        user_groups = user.groups.all()
        if user_groups.count():
            return cls.objects.filter(Q(constraint__in=constraints), Q(user=user) | Q(group__in=user_groups))
        else:
            return cls.objects.filter(constraint__in=constraints, user=user)
