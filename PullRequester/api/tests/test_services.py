from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from PullRequester.api.models import Team, User, PullRequest

import random
from unittest.mock import patch

