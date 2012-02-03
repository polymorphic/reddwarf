from nova import context
from nova import log as logging
from reddwarf import exception
from reddwarf.guest import api as guest_api
from nova.api.openstack import wsgi
from reddwarf.api import common

LOG = logging.getLogger('reddwarf.api.demo')
LOG.setLevel(logging.DEBUG)

class Controller(object):
    """ Demo E2E from API server to Agent instance """

    def __init__(self):
        self.guest_api = guest_api.API()
        super(Controller, self).__init__()


    def trigger_smart_agent(self, req, instance_id):
        """ Returns True if root is enabled for the given instance;
            False otherwise. """
        LOG.info("Call to demo for instance %s", instance_id)
        ctxt2 = context.get_admin_context()
        try:
            self.guest_api.trigger_smart_agent(ctxt2, instance_id)
            return {'status': 'done'}
        except Exception as err:
            LOG.error(err)
            raise exception.InstanceFault("Error triggering remote smart agent")

def create_resource(version='1.0'):
    controller = {
        '1.0': Controller,
        }[version]()

    metadata = {
        "attributes": {
            'user': ['name', 'password']
        },
        }

    xmlns = {
        '1.0': common.XML_NS_V10,
        }[version]

    serializers = {
        'application/xml': wsgi.XMLDictSerializer(metadata=metadata,
            xmlns=xmlns),
        }

    response_serializer = wsgi.ResponseSerializer(body_serializers=serializers)

    return wsgi.Resource(controller, serializer=response_serializer)