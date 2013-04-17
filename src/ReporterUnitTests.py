'''
This file is subject to the terms and conditions defined in the
LICENSE file, which is part of this source code package.
'''

import unittest
import Reporter

class ReporterUnitTests(unittest.TestCase):
    '''
    Test cases for the Reporter module.
    '''
    
    def setUp(self):
        '''
        Setup the test environment.
        '''
        pass
    
    def tearDown(self):
        '''
        Tear down the test environment.
        '''
        pass

    def test_init(self):
        '''
        It should create an object instance.
        '''
        reporter = Reporter()
        self.assertNotEqual(reporter, None)
    
if __name__ == '__main__':
    unittest.main()

    