
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


TACITURN_PROJECT_ROOT=/Users/johnk/PycharmProjects/Taciturn
TACITURN_ROOT=$TACITURN_PROJECT_ROOT/Taciturn

TACITURN_PYTHON_LIB=$TACITURN_ROOT/lib

TACITURN_VENV=$TACITURN_PROJECT_ROOT/venv
TACITURN_VENV_ACTIVATE=$TACITURN_VENV/bin/activate

WEBDRIVER_BIN=/Users/johnk/bin


if [[ ! -z "$TACITURN_VENV_ACTIVATE" ]]; then
  echo "Activating venv at '$TACITURN_VENV_ACTIVATE'"
  source $TACITURN_VENV_ACTIVATE
fi

if [[ ! -z "$WEBDRIVER_BIN" ]]; then
  echo "Adding webdriver executable path '$WEBDRIVER_BIN' to path."
  PATH=$WEBDRIVER_BIN:$PATH
fi

if [[ ! -z "$TACITURN_PYTHON_LIB" ]]; then
  echo "Adding taciturn library dir '$TACITURN_PYTHON_LIB' to python path."
  PYTHONPATH=$TACITURN_PYTHON_LIB:$PYTHONPATH
fi


export PATH
export PYTHONPATH
export FIREFOX_DRIVER
export CHROME_DRIVER
export TACITURN_ROOT
