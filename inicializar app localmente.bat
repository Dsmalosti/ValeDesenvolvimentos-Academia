@echo off
REM ===========================================================
REM  FLASK DEV - subir qualquer projeto Flask local para teste
REM  Autor: Adauto Netto
REM
REM  COMO USAR:
REM    Copie este arquivo para a RAIZ de qualquer projeto Flask
REM    e de dois cliques. Ele se vira sozinho.
REM
REM  O QUE ELE DETECTA AUTOMATICAMENTE:
REM    - nome da pasta do ambiente virtual (venv / .venv / env)
REM    - arquivo de entrada (app.py / run.py / wsgi.py / main.py)
REM    - primeira porta livre a partir da 5000
REM ===========================================================

setlocal enabledelayedexpansion
chcp 65001 >nul
title FLASK DEV - %~dp0

cd /d "%~dp0"

echo.
echo ===================================================
echo   FLASK DEV
echo   Pasta: %CD%
echo ===================================================
echo.

REM ==========================================================
REM  1. LOCALIZA O AMBIENTE VIRTUAL
REM ==========================================================
set "VENV="
if exist "venv\Scripts\activate.bat"  set "VENV=venv"
if not defined VENV if exist ".venv\Scripts\activate.bat" set "VENV=.venv"
if not defined VENV if exist "env\Scripts\activate.bat"   set "VENV=env"

if not defined VENV (
    echo [AVISO] Nenhum ambiente virtual encontrado aqui.
    echo.
    set /p CRIAR="Criar um agora com 'python -m venv venv'? (S/N): "
    if /i "!CRIAR!"=="S" (
        echo Criando ambiente virtual...
        python -m venv venv
        if errorlevel 1 (
            echo [ERRO] Falhou. O Python esta instalado e no PATH?
            echo        Teste com:  python --version
            pause
            exit /b 1
        )
        set "VENV=venv"
        set "INSTALAR=1"
    ) else (
        echo Cancelado. Sem venv nao da para continuar com seguranca.
        pause
        exit /b 1
    )
)

call "%VENV%\Scripts\activate.bat"
echo [OK] Ambiente virtual ativado: %VENV%

REM ==========================================================
REM  2. DEPENDENCIAS
REM ==========================================================
where flask >nul 2>&1
if errorlevel 1 set "INSTALAR=1"

if defined INSTALAR (
    if exist "requirements.txt" (
        echo [..] Instalando dependencias do requirements.txt
        pip install -r requirements.txt
    ) else (
        echo [AVISO] Flask nao encontrado e nao existe requirements.txt.
        echo         Instalando o Flask sozinho...
        pip install flask
    )
)
echo [OK] Dependencias prontas.

REM ==========================================================
REM  3. DESCOBRE O ARQUIVO DE ENTRADA
REM ==========================================================
REM  O Flask ja reconhece app.py e wsgi.py sozinho.
REM  Os outros precisam ser informados via FLASK_APP.
set "ALVO="
if exist "app.py"  set "ALVO=app.py"
if not defined ALVO if exist "wsgi.py" set "ALVO=wsgi.py"
if not defined ALVO if exist "run.py"  set "ALVO=run.py"
if not defined ALVO if exist "main.py" set "ALVO=main.py"

if not defined ALVO (
    echo [AVISO] Nao achei app.py / wsgi.py / run.py / main.py.
    echo         Se o projeto usa app factory, defina FLASK_APP no .env
    echo         Exemplo:  FLASK_APP=nome_do_pacote
    echo.
) else (
    set "FLASK_APP=!ALVO!"
    echo [OK] Entrada detectada: !ALVO!
)

REM  Modo desenvolvimento: reinicia sozinho ao salvar arquivo
set "FLASK_DEBUG=1"
set "FLASK_ENV=development"

REM ==========================================================
REM  4. ACHA UMA PORTA LIVRE (5000 ate 5010)
REM ==========================================================
set "PORTA="
for /l %%p in (5000,1,5010) do (
    if not defined PORTA (
        netstat -ano | find ":%%p " | find "LISTENING" >nul
        if errorlevel 1 set "PORTA=%%p"
    )
)

if not defined PORTA (
    echo [ERRO] Portas 5000 a 5010 todas ocupadas.
    echo        Feche outros servidores rodando e tente de novo.
    pause
    exit /b 1
)
echo [OK] Porta livre: %PORTA%

REM ==========================================================
REM  5. ABRE O NAVEGADOR COM ATRASO
REM ==========================================================
REM  O atraso existe para o servidor terminar de subir antes
REM  do navegador bater na porta.
start "abrindo navegador" /min cmd /c "timeout /t 4 /nobreak >nul && start http://127.0.0.1:%PORTA%"

REM ==========================================================
REM  6. SOBE O SERVIDOR
REM ==========================================================
echo.
echo ===================================================
echo   RODANDO EM: http://127.0.0.1:%PORTA%
echo.
echo   Esta janela e seu painel de log.
echo   Cada acesso no navegador aparece aqui embaixo.
echo   Status 200 = ok  ^|  404 = rota nao existe  ^|  500 = erro no codigo
echo.
echo   Para PARAR: Ctrl + C
echo   NAO feche esta janela enquanto estiver testando.
echo ===================================================
echo.

flask run --port=%PORTA%

REM ==========================================================
REM  7. SE CAIR, SEGURA A JANELA PARA VOCE LER O ERRO
REM ==========================================================
echo.
echo [SERVIDOR ENCERRADO]
echo Se caiu sozinho, a causa esta no traceback acima.
echo Leia de baixo para cima - a ultima linha e a causa real.
echo.
pause
endlocal
