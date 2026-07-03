# -*- coding: utf-8 -*-
"""Loader/resolver del manifiesto de cierre (shared/close-manifest.json).

Fuente UNICA de configuracion del cierre. Lo importan los steps python; el helper
shared/Get-CloseParams.ps1 lo invoca via `--emit-ps`. Nada lo consume todavia de
forma obligatoria: cada script que lo lee usa sus constantes actuales como default,
asi el comportamiento es identico hasta que se migre explicitamente.

API:
  load()                      -> dict del manifiesto (con .local overlay y env expandidas)
  cierre_month()              -> "2026-05"
  cierre_year_month()         -> (2026, 5)
  hub_root()                  -> Path expandida
  repo_root()                 -> Path del repo (derivada, no hardcodeada)
  inbox_dir()                 -> <hub>/_inbox/<closeMonth>
  segmentation(name)          -> dict de la regla (o None)
  line(name)                  -> dict de la linea (o None)
  resolve_source(name)        -> Path al archivo (inbox primero, luego legacyDir), o None

CLI:
  py shared/manifest.py --show
  py shared/manifest.py --get global.closeMonth
  py shared/manifest.py --segmentation magnus_split
  py shared/manifest.py --resolve iqvia_master
  py shared/manifest.py --emit-ps        # key=value para PowerShell
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / 'shared' / 'close-manifest.json'
LOCAL = REPO / 'shared' / 'close-manifest.local.json'


def _deep_merge(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _expand(s):
    """Expande ${VAR}/%VAR% de entorno en un string de path."""
    if not isinstance(s, str):
        return s
    return os.path.expandvars(s)


_cache = None


def load():
    global _cache
    if _cache is not None:
        return _cache
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if LOCAL.is_file():
        try:
            _deep_merge(data, json.loads(LOCAL.read_text(encoding='utf-8')))
        except Exception as e:
            print(f'WARN: close-manifest.local.json invalido, ignorado: {e}', file=sys.stderr)
    _cache = data
    return data


def repo_root():
    return REPO


def _g(*keys, default=None):
    d = load()
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def cierre_month():
    return _g('global', 'closeMonth')


def cierre_year_month():
    cm = cierre_month()
    y, m = cm.split('-')
    return int(y), int(m)


def cycle_folder():
    return _g('global', 'cycleFolder') or cierre_month()


def hub_root():
    return Path(_expand(_g('global', 'hubRoot', default='')))


def inbox_dir():
    return hub_root() / _g('global', 'inboxSubfolder', default='_inbox') / cierre_month()


def segmentation(name):
    return _g('segmentations', name)


def seg_get(name, key, default=None):
    """Devuelve segmentations[name][key] del manifiesto, o `default` si falta o si
    algo falla (nunca lanza). Patron para que los scripts lean la regla del manifiesto
    con su constante actual como fallback -> single-source sin romper si el manifiesto
    no esta. La fuente real de la regla es shared/close-manifest.json."""
    try:
        s = segmentation(name)
        if isinstance(s, dict) and key in s:
            return s[key]
    except Exception:
        pass
    return default


def line(name):
    return _g('lines', name)


def _newest(paths):
    paths = [p for p in paths if p.is_file()]
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def resolve_source(name):
    """Resuelve el archivo de una fuente: PRIMERO en _inbox/<closeMonth>/, y si no
    existe alli, cae al legacyDir actual (hub-relativo, con {cycleFolder} expandido).
    Devuelve la mas reciente que matchee el glob, o None. (Aditivo: con _inbox vacio,
    resuelve exactamente como hoy.)"""
    src = _g('sources', name)
    if not src:
        return None
    glob = src.get('glob', '*')
    # 1) inbox
    inbox = inbox_dir()
    if inbox.is_dir():
        hit = _newest(list(inbox.glob(glob)))
        if hit:
            return hit
    # 2) legacy
    legacy_rel = (src.get('legacyDir') or '').replace('{cycleFolder}', cycle_folder())
    legacy_dir = hub_root() / legacy_rel if legacy_rel else hub_root()
    if legacy_dir.is_dir():
        return _newest(list(legacy_dir.glob(glob)))
    return None


def _emit_ps():
    """Imprime key=value (una por linea) para que Get-CloseParams.ps1 los parsee."""
    out = {}
    out['CloseMonth'] = cierre_month()
    # ventaCutoff: ultimo mes COMPLETO de venta interna (puede ir ADELANTE de
    # closeMonth porque IQVIA reporta atrasado). Si se omite, cae a closeMonth.
    out['VentaCutoff'] = str(_g('global', 'ventaCutoff', default='') or cierre_month())
    out['CloseYear'] = str(_g('global', 'closeYear', default=''))
    out['CycleFolder'] = cycle_folder()
    out['HubRoot'] = str(hub_root())
    out['RepoRoot'] = str(repo_root())
    out['InboxDir'] = str(inbox_dir())
    for s in ('iqvia_master', 'venta_interna', 'ateneo_mat'):
        p = resolve_source(s)
        out['src_' + s] = str(p) if p else ''
    for k, v in out.items():
        print(f'{k}={v}')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--get')
    ap.add_argument('--segmentation')
    ap.add_argument('--line')
    ap.add_argument('--resolve')
    ap.add_argument('--emit-ps', action='store_true')
    a = ap.parse_args()
    if a.show:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
    elif a.get:
        print(_g(*a.get.split('.')))
    elif a.segmentation:
        print(json.dumps(segmentation(a.segmentation), ensure_ascii=False, indent=2))
    elif a.line:
        print(json.dumps(line(a.line), ensure_ascii=False, indent=2))
    elif a.resolve:
        p = resolve_source(a.resolve)
        print(p if p else '(no resuelto)')
    elif a.emit_ps:
        _emit_ps()
    else:
        # resumen util por default
        y, m = cierre_year_month()
        print(f'closeMonth={cierre_month()}  cycleFolder={cycle_folder()}  year/month={y}/{m}')
        print(f'hubRoot={hub_root()}')
        print(f'repoRoot={repo_root()}')
        print(f'inbox={inbox_dir()}  (existe={inbox_dir().is_dir()})')
        for s in ('iqvia_master', 'venta_interna', 'ateneo_mat'):
            print(f'  resolve {s}: {resolve_source(s)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
