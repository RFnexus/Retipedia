#!/bin/python3
import os
# Import the template 
import template 
# Import global settings 
import settings

### Micron Content ###
print(template.render_header())

if(settings.lxmf_address):
	print(f"Node Operator LXMF address: {settings.lxmf_address}")


print("This node is running Retipedia v2.0")
print("View the source code at https://github.com/RFnexus/Retipedia or at the rngit instance running on `!`[51b80676773cac13f4d5378fd2bb7c06]`")
print('`b')
print(".zim archives provided by the Kiwix project  https://library.kiwix.org")