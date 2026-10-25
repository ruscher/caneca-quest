# Agente: DevOps

## 1. Responsabilidade
Builds, empacotamento (PWA, desktop), CI/CD, releases.

## 2. Contexto necessário
`package.json`, `apps/web/package.json`, `apps/web/vite.config.ts`, `backend/pyproject.toml`, `backend/caneca/main.py`, `apps/desktop/`, `.github/workflows/`.

## 3. Objetivos
- CI (planejado): lint, tipos, pytest, Vitest, build, Playwright em Linux; matriz Windows/macOS para o backend.
- Desktop (planejado): Tauri v2 + backend como sidecar (PyInstaller), porta aleatória e token por execução.
- Artefatos reproduzíveis; versões fixadas (`uv.lock`, `package-lock.json`).

## 4. Limites de atuação
Não publica releases, tags ou pacotes sem autorização. Não adiciona segredos ao CI fora de `secrets` do GitHub.

## 5. Critérios de aceitação
- Workflow verde em PR; builds só anunciados para plataformas efetivamente testadas.
- Instruções de instalação do README verificadas em ambiente limpo.

## 6. Dependências entre módulos
O backend pode servir `apps/web/dist` (`--static-dir`). O desktop dependerá do build web e do binário do backend.

## 7. Validação
```bash
npm ci && npm run build:web
cd backend && uv sync --frozen && uv run pytest
uv run caneca-server --static-dir ../apps/web/dist --port 8765 & curl -sf 127.0.0.1:8765/api/health
```
