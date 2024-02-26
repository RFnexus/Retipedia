#!/bin/python3
import os
# Import the template 
import template 
# Import global settings 
import settings

header = '''
`c
''' + settings.node_title + ''' `F00f`_`[[Info`:/page/info.mu`]]`_`f`b
`a
-¯
Search: `B888`<search_query` >`b
`F0ff` `!`[Submit`:/page/results.mu`*|search_type='+search_type+']`!`b `f
-
'''