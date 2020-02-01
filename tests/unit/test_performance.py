"""
(c) 2019 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from network_importer.performance import print_from_ms


def test_print_from_ms():
    """
    Verify output of print from ms
    """

    assert print_from_ms(10) == "10ms"
    assert print_from_ms(1010) == "1s 10ms"
    assert print_from_ms(60010) == "1m 0s 10ms"
    assert print_from_ms(61010) == "1m 1s 10ms"
