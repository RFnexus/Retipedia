#!/bin/python3
import os
# Import the template 
import template 
# Import global settings 
import settings

### Micron Content ###
print(template.header)

if(settings.lxmf_address):
	print(f"Node Operator LXMF address: {settings.lxmf_address}")


print("This node is running Retipedia v1.0")
print("View the source code at https://github.com/RFnexus/Retipedia")
print('`b')
print(".zim archives provided by the Kiwix project  https://library.kiwix.org")