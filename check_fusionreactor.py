#!/usr/bin/env python

#
# A FusionReactor Nagios check script
#
# https://github.com/aparnachaudhary/nagios-plugin-jbossas7 is used as a reference for this.


#
# Main Author
#   - Christoph Witzany <christoph@web.crofting.com>
# Version: 0.1
# Github URL: https://github.com/doublemalt/nagios-plugin-fusionreactor
#
# USAGE
#
# See the README.asciidoc
#

import sys
import time
import optparse
import re
import os
import requests
import hashlib
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError, e:
        print e
        sys.exit(2)



#
# TODO: Document
#
def optional_arg(arg_default):
    def func(option, opt_str, value, parser):
        if parser.rargs and not parser.rargs[0].startswith('-'):
            val = parser.rargs[0]
            parser.rargs.pop(0)
        else:
            val = arg_default
        setattr(parser.values, option.dest, val)
    return func

#
# TODO: Document
#
def performance_data(perf_data, params):
    data = ''
    if perf_data:
        data = " |"
        for p in params:
            p += (None, None, None, None)
            param, param_name, warning, critical = p[0:4]
            data += "%s=%s" % (param_name, str(param))
            if warning or critical:
                warning = warning or 0
                critical = critical or 0
                data += ";%s;%s" % (warning, critical)

            data += " "

    return data


def numeric_type(param):
    """
    Checks parameter type
    True for float; int or null data; false otherwise

    :param param: input param to check
    """
    if ((type(param) == float or type(param) == int or param == None)):
        return True
    return False


def check_levels(param, warning, critical, message, ok=[]):
    """
    Checks error level

    :param param: input param
    :param warning: watermark for warning
    :param critical: watermark for critical
    :param message: message to be reported to nagios
    :param ok: watermark for ok level
    """
    if (numeric_type(critical) and numeric_type(warning)):
        if not numeric_type(param):
            param = float(param)
        if param >= critical:
            print "CRITICAL - " + message
            sys.exit(2)
        elif param >= warning:
            print "WARNING - " + message
            sys.exit(1)
        else:
            print "OK - " + message
            sys.exit(0)
    else:
        if param in critical:
            print "CRITICAL - " + message
            sys.exit(2)

        if param in warning:
            print "WARNING - " + message
            sys.exit(1)

        if param in ok:
            print "OK - " + message
            sys.exit(0)

        # unexpected param value
        print "CRITICAL - Unexpected value : " + str(param) + "; " + message
        return 2


def base_url(host, port, path):
    """
    Provides base URL for HTTP Management API

    :param host: FR hostname
    :param port: FR HTTP Management Port
    :param path: FR Path
    """

    url = "http://{host}:{port}/{path}/fService.cfm?command=remoting&subcommand=transfer&data=metrics".format(host=host, port=port, path=path)
    return url

def sub_char(character):
    char_map = {
        '0': '5',
        '1': '6',
        '2': '7',
        '3': '8',
        '4': '9',
        '5': '0',
        '6': '1',
        '7': '2',
        '8': '3',
        '9': '4',
        'A': 'N',
        'B': 'O',
        'C': 'P',
        'D': 'Q',
        'E': 'R',
        'F': 'S',
    }
    return char_map[character]

def get_stats_xml(conninfo):
    """
    HTTP GET with Basic Authentication. Returns XML result.

    :param conninfo: FR connection parameters
    """
    try:
        hash = hashlib.md5()
        hash.update(conninfo['password'])

        password_hash = hash.hexdigest().upper()
        password_hash_subbed = ''.join([sub_char(character) for character in password_hash])


        url = base_url(conninfo['host'], conninfo['port'], conninfo['subdir'])

        headers = {'content-type': 'text/plain'}
        #res = requests.get(url, headers=headers, auth=HTTPBasicAuth(conninfo['user'], conninfo['password']))
        res = requests.get(url, headers=headers, auth=HTTPBasicAuth('NoUser', password_hash_subbed))

        return res.text
    except Exception, e:
        import traceback
        traceback.print_exc()
        # The server could be down; make this CRITICAL.
        print "CRITICAL - FR Error:", e
        sys.exit(2)

def main(argv):

    p = optparse.OptionParser(conflict_handler="resolve", description="This Nagios plugin checks parameters collected by FusionReactor.")

    p.add_option('-H', '--host', action='store', type='string', dest='host', default='127.0.0.1', help='The hostname you want to connect to')
    p.add_option('-P', '--port', action='store', type='int', dest='port', default=9990, help='The port FusionReactor is runnung on')
    p.add_option('-s', '--subdir', action='store', type='string', dest='subdir', default=None, help='The path of the FusionReactor API')
    p.add_option('-u', '--user', action='store', type='string', dest='user', default=None, help='The username you want to login as')
    p.add_option('-p', '--pass', action='store', type='string', dest='passwd', default=None, help='The password you want to use for that user')
    p.add_option('-W', '--warning', action='store', dest='warning', default=None, help='The warning threshold we want to set')
    p.add_option('-C', '--critical', action='store', dest='critical', default=None, help='The critical threshold we want to set')
    p.add_option('-D', '--perf_data', action='store_true', dest='perf_data', default=False, help='return performance data')
    p.add_option('-f', '--field', action='store', type='string', dest='field', default='server_status', help='The field you want to query')

    options, arguments = p.parse_args()
    conninfo = {'host': options.host, 'port': options.port, 'subdir': options.subdir, 'user': options.user, 'password': options.passwd}

    warning = float(options.warning or 0)
    critical = float(options.critical or 0)

    field = options.field
    perf_data = options.perf_data



    return check_field(field, conninfo, warning, critical, perf_data)


def exit_with_general_warning(e):
    """

    :param e: exception
    """
    if isinstance(e, SystemExit):
        return e
    elif isinstance(e, ValueError):
        print "WARNING - General FR Warning:", e
        sys.exit(1)
    else:
        print "WARNING - General FR Warning:", e
        sys.exit(1)


def exit_with_general_critical(e):
    if isinstance(e, SystemExit):
        return e
    elif isinstance(e, ValueError):
        print "CRITICAL - General FR Error:", e
        sys.exit(2)
    else:
        print "CRITICAL - General FR Error:", e
        sys.exit(2)

def get_field_data(conninfo, field_path):

    try:
        res = get_stats_xml(conninfo)

        doc = ElementTree.fromstring(res)

        return doc.find(field_path).text
    except Exception, e:
        return exit_with_general_critical(e)

def check_field(field, conninfo, warning, critical, perf_data):
    warning = warning or 1
    critical = critical or 5

    try:
        field_value = get_field_data(conninfo, field)

        message = "%s: %s" % (field, field_value)
        message += performance_data(perf_data, [(field_value, field, warning, critical)])

        return check_levels(field_value, warning, critical, message)
    except Exception, e:
        return exit_with_general_critical(e)





def build_file_name(host, action):
    # done this way so it will work when run independently and from shell
    module_name = re.match('(.*//*)*(.*)\..*', __file__).group(2)
    return "/tmp/" + module_name + "_data/" + host + "-" + action + ".data"


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)


def write_values(file_name, string):
    f = None
    try:
        f = open(file_name, 'w')
    except IOError, e:
        # try creating
        if (e.errno == 2):
            ensure_dir(file_name)
            f = open(file_name, 'w')
        else:
            raise IOError(e)
    f.write(string)
    f.close()
    return 0


def read_values(file_name):
    data = None
    try:
        f = open(file_name, 'r')
        data = f.read()
        f.close()
        return 0, data
    except IOError, e:
        if (e.errno == 2):
            # no previous data
            return 1, ''
    except Exception, e:
        return 2, None


def calc_delta(old, new):
    delta = []
    if (len(old) != len(new)):
        raise Exception("unequal number of parameters")
    for i in range(0, len(old)):
        val = float(new[i]) - float(old[i])
        if val < 0:
            val = new[i]
        delta.append(val)
    return 0, delta


def maintain_delta(new_vals, host, action):
    file_name = build_file_name(host, action)
    err, data = read_values(file_name)
    old_vals = data.split(';')
    new_vals = [str(int(time.time()))] + new_vals
    delta = None
    try:
        err, delta = calc_delta(old_vals, new_vals)
    except:
        err = 2
    write_res = write_values(file_name, ";" . join(str(x) for x in new_vals))
    return err + write_res, delta


#
# main app
#
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
