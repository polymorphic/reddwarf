from nova import context
from nova import log as logging
from reddwarf import exception
from reddwarf.guest import api as guest_api
from nova.api.openstack import wsgi
from reddwarf.api import common
from webob import exc

LOG = logging.getLogger('reddwarf.api.demo')
LOG.setLevel(logging.DEBUG)

class Controller(object):
    """ Demo E2E from API server to Agent instance """

    def __init__(self):
        self.guest_api = guest_api.API()
        super(Controller, self).__init__()

    def cast_smart_agent(self, req, instance_id):
        LOG.info("Call to demo asynchronous call to smart agent on instance %s", instance_id)
        ctxt = context.get_admin_context()
        try:
            result = self.guest_api.cast_smart_agent(ctxt, instance_id)
            return exc.HTTPAccepted()
        except Exception as err:
            LOG.error(err)
            raise exception.InstanceFault("Error triggering remote smart agent")

    def call_smart_agent(self, req, instance_id):
        """  """
        LOG.info("Call to demo synchronous call to smart agent on instance %s", instance_id)
        ctxt = context.get_admin_context()
        try:
            result = self.guest_api.call_smart_agent(ctxt, instance_id)
            return {'Response': str(result)}
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