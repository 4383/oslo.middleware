# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Base class(es) for WSGI Middleware."""

from inspect import getargspec
import webob.dec

from oslo_config import cfg


class Middleware(object):
    """Base WSGI middleware wrapper.

    These classes require an application to be initialized that will be called
    next.  By default the middleware will simply call its wrapped app, or you
    can override __call__ to customize its behavior.
    """

    @classmethod
    def factory(cls, global_conf, **local_conf):
        """Factory method for paste.deploy."""
        conf = global_conf.copy() if global_conf else {}
        conf.update(local_conf)

        def middleware_filter(app):
            return cls(app, conf)

        return middleware_filter

    def __init__(self, application, conf=None):
        self.application = application
        # NOTE(sileht): If the configuration come from oslo.config
        # just use it.
        if isinstance(conf, cfg.ConfigOpts):
            self.conf = []
            self.oslo_conf = conf
        else:
            self.conf = conf or []
            if "oslo_config_project" in self.conf:
                if 'oslo_config_file' in self.conf:
                    default_config_files = [self.conf['oslo_config_file']]
                else:
                    default_config_files = None
                self.oslo_conf = cfg.ConfigOpts()
                self.oslo_conf([], project=self.conf['oslo_config_project'],
                               default_config_files=default_config_files,
                               validate_default_values=True)

            else:
                # Fallback to global object
                self.oslo_conf = cfg.CONF

    def process_request(self, req):
        """Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.
        """
        return None

    def process_response(self, response, request=None):
        """Do whatever you'd like to the response."""
        return response

    @webob.dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        if response:
            return response
        response = req.get_response(self.application)

        (args, varargs, varkw, defaults) = getargspec(self.process_response)
        if 'request' in args:
            return self.process_response(response, request=req)
        return self.process_response(response)
