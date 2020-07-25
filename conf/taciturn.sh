
# This file is part of the Taciturn web automation framework.
#
# Taciturn is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tactiurn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tactiurn.  If not, see <https://www.gnu.org/licenses/>.


# environment for running Taciturn stuff!

WEBDRIVER_BIN=/Users/johnk/bin
PYTHON_LIB_PREFIX=/Users/johnk/PycharmProjects/Taciturn/Taciturn/lib
FIREFOX_DRIVER=$WEBDRIVER_BIN/geckodriver
CHROME_DRIVER=$WEBDRIVER_BIN/chromedriver
TACITURN_ROOT=/Users/johnk/PycharmProjects/Taciturn/Taciturn

if [[ ! -z "$WEBDRIVER_BIN" ]]; then
  echo "Adding webdriver path '$WEBDRIVER_BIN' to path."
  PATH=$WEBDRIVER_BIN:$PATH
fi

if [[ ! -z "$PYTHONPATH" ]]; then
  echo "Adding taciturn path '$PYTHON_LIB_PREFIX' to python path."
  PYTHONPATH=$PYTHON_LIB_PREFIX:$PYTHONPATH
else
  PYTHONPATH=$PYTHON_LIB_PREFIX
fi

export PATH
export PYTHONPATH
export FIREFOX_DRIVER
export CHROME_DRIVER
export TACITURN_ROOT

