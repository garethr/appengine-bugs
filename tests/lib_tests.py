#!/usr/bin/env python

import sys
import os
import unittest

# insert application path
app_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../'
)
sys.path.insert(0, app_path)


from lib import slugify, textile

class SlugifyTest(unittest.TestCase):

    def test_slugify(self):  
        tests = [
            ['test','test'],
            ['test test','test-test'],
            ['test&^%','test'],
            ['test_test','testtest'],
        ]
        for input, output in tests:
            self.assertEqual(slugify(input), output)

class TextileTest(unittest.TestCase):
    
    def disabled_test_textile(self):
        tests = [
            ['test','<p>test</p>'],
            ['<script src="evil">evil</script>',''],
            ['h1. test','<h1>test</h1>'],
            ['pre. test','<pre>test\n</pre>'],
        ]
        for input, output in tests:
            self.assertEqual(textile(input), output)
                
                                       
if __name__ == "__main__":
    unittest.main()