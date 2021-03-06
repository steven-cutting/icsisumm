# Natural Language Toolkit - InvalidDataError 
#  Is thrown when the input data entered by the user is invalid
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier.exceptions import SimpleError

class InvalidDataError(SimpleError):
    pass