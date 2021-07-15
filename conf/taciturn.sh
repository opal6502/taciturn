
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


TACITURN_PROJECT_ROOT="/Users/johnk/PycharmProjects/Taciturn"
TACITURN_ROOT="$TACITURN_PROJECT_ROOT/Taciturn"

TACITURN_PYTHON_LIB="$TACITURN_ROOT/lib"

TACITURN_VENV="$TACITURN_PROJECT_ROOT/venv"
TACITURN_VENV_ACTIVATE="$TACITURN_VENV/bin/activate"

WEBDRIVER_BIN="/Users/johnk/bin"


if [[ ! -z "$TACITURN_VENV_ACTIVATE" ]]; then
  echo "Run . $TACITURN_VENV_ACTIVATE"
  source $TACITURN_VENV_ACTIVATE
else
  echo "WARNING: TACITURN_VENV_ACTIVATE is not set." >&2
fi

if [[ ! -z "PYTHONPATH" ]]; then
  PYTHONPATH=$TACITURN_PYTHON_LIB:$PYTHONPATH
else
  PYTHONPATH="$TACITURN_PYTHON_LIB"
fi
echo "Set PYTHONPATH=$PYTHONPATH"

if [[ ! -z "$WEBDRIVER_BIN" ]]; then
  PATH=$WEBDRIVER_BIN:$PATH
  echo "Set PATH+=$WEBDRIVER_BIN"
fi

# Taciturn database URL:

if [[ -z "TACITURN_DATABASE_PASSWORD" ]]; then
  echo "WARNING: TACITURN_DATABASE_PASSWORD is not defined." >&2
fi

TACITURN_DATABASE_USER=${TACITURN_DATABASE_USER:=taciturn}
TACITURN_DATABASE_PASSWORD=${TACITURN_DATABASE_PASSWORD:=setpassword}
TACITURN_DATABASE_HOST=${TACITURN_DATABASE_HOST:=localhost}
TACITURN_DATABASE_NAME=${TACITURN_DATABASE_NAME:=taciturn}

TACITURN_DATABASE_URL="postgresql+psycopg2://$TACITURN_DATABASE_USER:$TACITURN_DATABASE_PASSWORD@$TACITURN_DATABASE_HOST/$TACITURN_DATABASE_NAME"
TACITURN_DATABASE_URL_DISPLAY="postgresql+psycopg2://$TACITURN_DATABASE_USER:**********@$TACITURN_DATABASE_HOST/$TACITURN_DATABASE_NAME"

echo "Set TACITURN_DATABASE_URL=$TACITURN_DATABASE_URL_DISPLAY"

export PATH
export PYTHONPATH
export FIREFOX_DRIVER
export CHROME_DRIVER
export TACITURN_ROOT
export TACITURN_DATABASE_URL
