
import deprecation

from qgis.core import QgsWkbTypes

class MetadataVectorLayer(object):
    """
    Object to manage metadata QGIS vector layer
    """

    def __init__(self, qgis_layer, client_var, relation_id=None, lock=None, **kwargs):
        """Constructor

        :param qgis_layer: the QGIS vector layer
        :type qgis_layer: QgsVectorLayer
        :param client_var: layer original name
        :type client_var: str
        :param relation_id: relation id, defaults to None
        :type relation_id: str, optional
        :param lock: [description], defaults to None
        :type lock: [type], optional
        """
        self.qgis_layer = qgis_layer
        self.geometry_type = QgsWkbTypes.geometryDisplayString(qgis_layer.geometryType())
        self.client_var = client_var
        self.relation_id = relation_id
        self.lock = lock

        for k, v in list(kwargs.items()):
            setattr(self, k, v)

    def get_feature(self, pk):
        """
        Returns a (possibly invalid) single feature from QGIS layer
        """

        return self.qgis_layer.getFeature(pk)
