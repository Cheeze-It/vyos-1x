#!/usr/bin/env python3
#
# Copyright (C) 2019-2020 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from copy import deepcopy
from sys import exit
from netifaces import interfaces

from vyos.ifconfig import BridgeIf, Section
from vyos.ifconfig.stp import STP
from vyos.configdict import list_diff
from vyos.config import Config
from vyos.util import cmd
from vyos import ConfigError

default_config_data = {
    'address': [],
    'address_remove': [],
    'aging': 300,
    'arp_cache_tmo': 30,
    'description': '',
    'deleted': False,
    'dhcp_client_id': '',
    'dhcp_hostname': '',
    'dhcp_vendor_class_id': '',
    'dhcpv6_prm_only': False,
    'dhcpv6_temporary': False,
    'disable': False,
    'disable_link_detect': 1,
    'forwarding_delay': 14,
    'hello_time': 2,
    'ip_disable_arp_filter': 1,
    'ip_enable_arp_accept': 0,
    'ip_enable_arp_announce': 0,
    'ip_enable_arp_ignore': 0,
    'ipv6_autoconf': 0,
    'ipv6_eui64_prefix': [],
    'ipv6_eui64_prefix_remove': [],
    'ipv6_forwarding': 1,
    'ipv6_dup_addr_detect': 1,
    'igmp_querier': 0,
    'intf': '',
    'mac' : '',
    'max_age': 20,
    'member': [],
    'member_remove': [],
    'priority': 32768,
    'stp': 0,
    'vrf': ''
}

def get_config():
    bridge = deepcopy(default_config_data)
    conf = Config()

    # determine tagNode instance
    if 'VYOS_TAGNODE_VALUE' not in os.environ:
        raise ConfigError('Interface (VYOS_TAGNODE_VALUE) not specified')

    bridge['intf'] = os.environ['VYOS_TAGNODE_VALUE']

    # Check if bridge has been removed
    if not conf.exists('interfaces bridge ' + bridge['intf']):
        bridge['deleted'] = True
        return bridge

    # set new configuration level
    conf.set_level('interfaces bridge ' + bridge['intf'])

    # retrieve configured interface addresses
    if conf.exists('address'):
        bridge['address'] = conf.return_values('address')

    # Determine interface addresses (currently effective) - to determine which
    # address is no longer valid and needs to be removed
    eff_addr = conf.return_effective_values('address')
    bridge['address_remove'] = list_diff(eff_addr, bridge['address'])

    # retrieve aging - how long addresses are retained
    if conf.exists('aging'):
        bridge['aging'] = int(conf.return_value('aging'))

    # retrieve interface description
    if conf.exists('description'):
        bridge['description'] = conf.return_value('description')

    # get DHCP client identifier
    if conf.exists('dhcp-options client-id'):
        bridge['dhcp_client_id'] = conf.return_value('dhcp-options client-id')

    # DHCP client host name (overrides the system host name)
    if conf.exists('dhcp-options host-name'):
        bridge['dhcp_hostname'] = conf.return_value('dhcp-options host-name')

    # DHCP client vendor identifier
    if conf.exists('dhcp-options vendor-class-id'):
        bridge['dhcp_vendor_class_id'] = conf.return_value('dhcp-options vendor-class-id')

    # DHCPv6 only acquire config parameters, no address
    if conf.exists('dhcpv6-options parameters-only'):
        bridge['dhcpv6_prm_only'] = True

    # DHCPv6 temporary IPv6 address
    if conf.exists('dhcpv6-options temporary'):
        bridge['dhcpv6_temporary'] = True

    # Disable this bridge interface
    if conf.exists('disable'):
        bridge['disable'] = True

    # Ignore link state changes
    if conf.exists('disable-link-detect'):
        bridge['disable_link_detect'] = 2

    # Forwarding delay
    if conf.exists('forwarding-delay'):
        bridge['forwarding_delay'] = int(conf.return_value('forwarding-delay'))

    # Hello packet advertisment interval
    if conf.exists('hello-time'):
        bridge['hello_time'] = int(conf.return_value('hello-time'))

    # Enable Internet Group Management Protocol (IGMP) querier
    if conf.exists('igmp querier'):
        bridge['igmp_querier'] = 1

    # ARP cache entry timeout in seconds
    if conf.exists('ip arp-cache-timeout'):
        bridge['arp_cache_tmo'] = int(conf.return_value('ip arp-cache-timeout'))

    # ARP filter configuration
    if conf.exists('ip disable-arp-filter'):
        bridge['ip_disable_arp_filter'] = 0

    # ARP enable accept
    if conf.exists('ip enable-arp-accept'):
        bridge['ip_enable_arp_accept'] = 1

    # ARP enable announce
    if conf.exists('ip enable-arp-announce'):
        bridge['ip_enable_arp_announce'] = 1

    # ARP enable ignore
    if conf.exists('ip enable-arp-ignore'):
        bridge['ip_enable_arp_ignore'] = 1

    # Enable acquisition of IPv6 address using stateless autoconfig (SLAAC)
    if conf.exists('ipv6 address autoconf'):
        bridge['ipv6_autoconf'] = 1

    # Get prefixes for IPv6 addressing based on MAC address (EUI-64)
    if conf.exists('ipv6 address eui64'):
        bridge['ipv6_eui64_prefix'] = conf.return_values('ipv6 address eui64')

    # Determine currently effective EUI64 addresses - to determine which
    # address is no longer valid and needs to be removed
    eff_addr = conf.return_effective_values('ipv6 address eui64')
    bridge['ipv6_eui64_prefix_remove'] = list_diff(eff_addr, bridge['ipv6_eui64_prefix'])

    # Remove the default link-local address if set.
    if conf.exists('ipv6 address no-default-link-local'):
        bridge['ipv6_eui64_prefix_remove'].append('fe80::/64')
    else:
        # add the link-local by default to make IPv6 work
        bridge['ipv6_eui64_prefix'].append('fe80::/64')

    # Disable IPv6 forwarding on this interface
    if conf.exists('ipv6 disable-forwarding'):
        bridge['ipv6_forwarding'] = 0

    # IPv6 Duplicate Address Detection (DAD) tries
    if conf.exists('ipv6 dup-addr-detect-transmits'):
        bridge['ipv6_dup_addr_detect'] = int(conf.return_value('ipv6 dup-addr-detect-transmits'))

    # Media Access Control (MAC) address
    if conf.exists('mac'):
        bridge['mac'] = conf.return_value('mac')

    # Find out if MAC has changed - if so, we need to delete all IPv6 EUI64 addresses
    # before re-adding them
    if ( bridge['mac'] and bridge['intf'] in Section.interfaces(section='bridge')
             and bridge['mac'] != BridgeIf(bridge['intf'], create=False).get_mac() ):
        bridge['ipv6_eui64_prefix_remove'] += bridge['ipv6_eui64_prefix']

    # Interval at which neighbor bridges are removed
    if conf.exists('max-age'):
        bridge['max_age'] = int(conf.return_value('max-age'))

    # Determine bridge member interface (currently configured)
    for intf in conf.list_nodes('member interface'):
        # cost and priority initialized with linux defaults
        # by reading /sys/devices/virtual/net/br0/brif/eth2/{path_cost,priority}
        # after adding interface to bridge after reboot
        iface = {
            'name': intf,
            'cost': 100,
            'priority': 32
        }

        if conf.exists('member interface {} cost'.format(intf)):
            iface['cost'] = int(conf.return_value('member interface {} cost'.format(intf)))

        if conf.exists('member interface {} priority'.format(intf)):
            iface['priority'] = int(conf.return_value('member interface {} priority'.format(intf)))

        bridge['member'].append(iface)

    # Determine bridge member interface (currently effective) - to determine which
    # interfaces is no longer assigend to the bridge and thus can be removed
    eff_intf = conf.list_effective_nodes('member interface')
    act_intf = conf.list_nodes('member interface')
    bridge['member_remove'] = list_diff(eff_intf, act_intf)

    # Priority for this bridge
    if conf.exists('priority'):
        bridge['priority'] = int(conf.return_value('priority'))

    # Enable spanning tree protocol
    if conf.exists('stp'):
        bridge['stp'] = 1

    # retrieve VRF instance
    if conf.exists('vrf'):
        bridge['vrf'] = conf.return_value('vrf')

    return bridge

def verify(bridge):
    if bridge['dhcpv6_prm_only'] and bridge['dhcpv6_temporary']:
        raise ConfigError('DHCPv6 temporary and parameters-only options are mutually exclusive!')

    vrf_name = bridge['vrf']
    if vrf_name and vrf_name not in interfaces():
        raise ConfigError(f'VRF "{vrf_name}" does not exist')

    conf = Config()
    for br in conf.list_nodes('interfaces bridge'):
        # it makes no sense to verify ourself in this case
        if br == bridge['intf']:
            continue

        for intf in bridge['member']:
            tmp = conf.list_nodes('interfaces bridge {} member interface'.format(br))
            if intf['name'] in tmp:
                raise ConfigError('Interface "{}" belongs to bridge "{}" and can not be enslaved.'.format(intf['name'], bridge['intf']))

    # the interface must exist prior adding it to a bridge
    for intf in bridge['member']:
        if intf['name'] not in interfaces():
            raise ConfigError('Can not add non existing interface "{}" to bridge "{}"'.format(intf['name'], bridge['intf']))

        if intf['name'] == 'lo':
            raise ConfigError('Loopback interface "lo" can not be added to a bridge')

    # bridge members are not allowed to be bond members, too
    for intf in bridge['member']:
        for bond in conf.list_nodes('interfaces bonding'):
            if conf.exists('interfaces bonding ' + bond + ' member interface'):
                if intf['name'] in conf.return_values('interfaces bonding ' + bond + ' member interface'):
                    raise ConfigError('Interface {} belongs to bond {}, can not add it to {}'.format(intf['name'], bond, bridge['intf']))

    return None

def generate(bridge):
    return None

def apply(bridge):
    br = BridgeIf(bridge['intf'])

    if bridge['deleted']:
        # delete interface
        br.remove()
    else:
        # enable interface
        br.set_admin_state('up')
        # set ageing time
        br.set_ageing_time(bridge['aging'])
        # set bridge forward delay
        br.set_forward_delay(bridge['forwarding_delay'])
        # set hello time
        br.set_hello_time(bridge['hello_time'])
        # configure ARP filter configuration
        br.set_arp_filter(bridge['ip_disable_arp_filter'])
        # configure ARP accept
        br.set_arp_accept(bridge['ip_enable_arp_accept'])
        # configure ARP announce
        br.set_arp_announce(bridge['ip_enable_arp_announce'])
        # configure ARP ignore
        br.set_arp_ignore(bridge['ip_enable_arp_ignore'])
        # IPv6 address autoconfiguration
        br.set_ipv6_autoconf(bridge['ipv6_autoconf'])
        # IPv6 forwarding
        br.set_ipv6_forwarding(bridge['ipv6_forwarding'])
        # IPv6 Duplicate Address Detection (DAD) tries
        br.set_ipv6_dad_messages(bridge['ipv6_dup_addr_detect'])
        # set max message age
        br.set_max_age(bridge['max_age'])
        # set bridge priority
        br.set_priority(bridge['priority'])
        # turn stp on/off
        br.set_stp(bridge['stp'])
        # enable or disable IGMP querier
        br.set_multicast_querier(bridge['igmp_querier'])
        # update interface description used e.g. within SNMP
        br.set_alias(bridge['description'])

        if bridge['dhcp_client_id']:
            br.dhcp.v4.options['client_id'] = bridge['dhcp_client_id']

        if bridge['dhcp_hostname']:
            br.dhcp.v4.options['hostname'] = bridge['dhcp_hostname']

        if bridge['dhcp_vendor_class_id']:
            br.dhcp.v4.options['vendor_class_id'] = bridge['dhcp_vendor_class_id']

        if bridge['dhcpv6_prm_only']:
            br.dhcp.v6.options['dhcpv6_prm_only'] = True

        if bridge['dhcpv6_temporary']:
            br.dhcp.v6.options['dhcpv6_temporary'] = True

        # assign/remove VRF
        br.set_vrf(bridge['vrf'])

        # Delete old IPv6 EUI64 addresses before changing MAC
        # (adding members to a fresh bridge changes its MAC too)
        for addr in bridge['ipv6_eui64_prefix_remove']:
            br.del_ipv6_eui64_address(addr)

        # remove interface from bridge
        for intf in bridge['member_remove']:
            br.del_port(intf)

        # add interfaces to bridge
        for member in bridge['member']:
            # flushes address of only children of Interfaces class
            # (e.g. vlan are not)
            if member['name'] in Section.interfaces():
                klass = Section.klass(member['name'], vlan=False)
                klass(member['name'], create=False).flush_addrs()
            # flushes all interfaces
            cmd(f'ip addr flush dev "{member["name"]}"')
            br.add_port(member['name'])

        # Change interface MAC address
        if bridge['mac']:
            br.set_mac(bridge['mac'])

        # Add IPv6 EUI-based addresses (must be done after adding the
        # 1st bridge member or setting its MAC)
        for addr in bridge['ipv6_eui64_prefix']:
            br.add_ipv6_eui64_address(addr)

        # up/down interface
        if bridge['disable']:
            br.set_admin_state('down')

        # Configure interface address(es)
        # - not longer required addresses get removed first
        # - newly addresses will be added second
        for addr in bridge['address_remove']:
            br.del_addr(addr)
        for addr in bridge['address']:
            br.add_addr(addr)

        STPBridgeIf = STP.enable(BridgeIf)
        # configure additional bridge member options
        for member in bridge['member']:
            i = STPBridgeIf(member['name'])
            # configure ARP cache timeout
            i.set_arp_cache_tmo(bridge['arp_cache_tmo'])
            # ignore link state changes
            i.set_link_detect(bridge['disable_link_detect'])
            # set bridge port path cost
            i.set_path_cost(member['cost'])
            # set bridge port path priority
            i.set_path_priority(member['priority'])

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
