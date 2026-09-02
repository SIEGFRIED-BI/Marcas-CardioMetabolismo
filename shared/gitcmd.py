# -*- coding: utf-8 -*-
"""Resuelve el ejecutable de git.

POR QUE EXISTE: varios scripts (verify-history-preserved, preserve-early-history,
check-forma-vs-baseline, ...) leen la baseline con `subprocess.run(['git', ...])`.
Eso funciona cuando los lanza el pre-commit hook (git corre sus hooks con git en el
PATH) pero CRASHEA con FileNotFoundError cuando los lanza update-all.ps1 desde
PowerShell, porque en esta maquina git NO esta en el PATH de usuario. Resultado: el
cierre mensual reportaba "GATE history FALLO" en todas las corridas -- el gate que
protege contra perder meses historicos (regla #7 de CLAUDE.md) no se estaba
ejecutando, y el error se leia como si el gate hubiera encontrado un problema.

Uso:
    from gitcmd import git_show, GIT
    texto = git_show('HEAD', 'cardio/data.js', cwd=REPO)   # '' si no existe
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path


def _find_git():
    hit = shutil.which('git')
    if hit:
        return hit
    cands = [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Git' / 'cmd' / 'git.exe',
        Path(os.environ.get('ProgramFiles', '')) / 'Git' / 'cmd' / 'git.exe',
        Path(os.environ.get('ProgramFiles(x86)', '')) / 'Git' / 'cmd' / 'git.exe',
        Path('/usr/bin/git'),
    ]
    for c in cands:
        try:
            if c.is_file():
                return str(c)
        except OSError:
            continue
    return 'git'   # ultimo recurso: que falle con el mensaje de siempre


GIT = _find_git()


def git_show(ref, path, cwd=None):
    """Contenido de `path` en `ref`. Devuelve '' si git falla o el path no existe alli."""
    r = subprocess.run([GIT, '--no-pager', 'show', f'{ref}:{path}'],
                       cwd=str(cwd) if cwd else None, capture_output=True)
    if r.returncode != 0:
        return ''
    return r.stdout.decode('utf-8-sig', errors='replace')


def available():
    """True si git responde (para que un gate pueda declararse AUSENTE, no PASADO)."""
    try:
        return subprocess.run([GIT, '--version'], capture_output=True).returncode == 0
    except OSError:
        return False
