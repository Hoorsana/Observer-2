REM SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
REM
REM SPDX-License-Identifier: CC0-1.0

SET VENV=.venv
SET PYTHON=%VENV%\Scripts\python.exe
SET PIP=%VENV%\Scripts\pip.exe
SET PYTEST=%VENV%\Scripts\pytest.exe

IF /I "%1"=="default" GOTO default
IF /I "%1"=="cli" GOTO cli
IF /I "%1"=="core" GOTO core
IF /I "%1"=="live" GOTO live
IF /I "%1"=="simulink" GOTO live
IF /I "%1"=="quick" GOTO quick
IF /I "%1"=="example" GOTO example
IF /I "%1"=="venv" GOTO venv
IF /I "%1"=="sphinx" GOTO sphinx
IF /I "%1"=="clean" GOTO clean
IF /I "%1"=="install" GOTO install
GOTO error

:default
	CALL make.bat venv
	. %VENV%\Scripts\activate && pytest -vv tests\ && deactivate
	GOTO :EOF

:cli
	CALL make.bat venv
	%VENV%\Scripts\activate && pytest -vv tests\test_pylab_cli.py && deactivate
	GOTO :EOF

:core
	CALL make.bat venv
	%PYTEST% -vv tests\core
	GOTO :EOF

:simulink
  CALL make.bat venv
  %PYTEST% -vv tests\simulink
  GOTO :EOF

:live
	CALL make.bat venv
	%PYTEST% -vv tests\live
	GOTO :EOF

:quick
	CALL make.bat venv
	CALL make.bat core
	CALL make.bat cli
	GOTO :EOF

:example
	CALL make.bat venv
	%PYTEST% -vv example
	GOTO :EOF

:venv
	pip install virtualenv

	if NOT exist %VENV% virtualenv %VENV%
	%PIP% install -r requirements.txt
	if defined PYLAB_MATLAB_PATH (
            PUSHD %PYLAB_MATLAB_PATH%/extern/engines/python
            python setup.py install
            POPD
        )
	%PYTHON% setup.py install
	%PYTHON% setup.py install_scripts
	GOTO :EOF

:sphinx
	sphinx-apidoc --module-first --force --private --separate -o docs/build src
	PUSHD docs && make html && POPD
	GOTO :EOF

:clean
  python setup.py clean
	if exist build rmdir /Q /s build
	if exist %VENV% rmdir /Q /s %VENV%
	if exist docs\build rmdir /Q /s docs\build
	GOTO :EOF

:install
	python setup.py install
	python setup.py install_scripts
	GOTO :EOF

:error
    IF "%1"=="" (
        ECHO make: *** No targets specified and no makefile found.  Stop.
    ) ELSE (
        ECHO make: *** No rule to make target '%1%'. Stop.
    )
    GOTO :EOF
