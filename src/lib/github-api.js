/**
 * GitHub API - Modulo compartilhado para carregar editais dinamicamente.
 * Todas as paginas usam este modulo para buscar dados em tempo real.
 */

const REPO_CONFIG = {
  owner: 'esevero',
  repo: 'analisador_edital',
  branch: 'main',
  contentPath: 'content/editais',
};

export function getToken() {
  return localStorage.getItem('gh_pat') || '';
}

export function saveToken(token) {
  localStorage.setItem('gh_pat', token.trim());
}

export function clearToken() {
  localStorage.removeItem('gh_pat');
}

export function getRepoConfig() {
  return REPO_CONFIG;
}

/**
 * Decodifica base64 preservando UTF-8
 */
export function decodeBase64UTF8(base64) {
  const binStr = atob(base64.replace(/\n/g, ''));
  const bytes = new Uint8Array(binStr.length);
  for (let i = 0; i < binStr.length; i++) {
    bytes[i] = binStr.charCodeAt(i);
  }
  return new TextDecoder('utf-8').decode(bytes);
}

/**
 * Codifica string para base64 preservando UTF-8
 */
export function encodeBase64UTF8(str) {
  const bytes = new TextEncoder().encode(str);
  let binStr = '';
  for (let i = 0; i < bytes.length; i++) {
    binStr += String.fromCharCode(bytes[i]);
  }
  return btoa(binStr);
}

/**
 * Parser YAML simples (flat + 1 nivel aninhado + listas)
 */
function parseSimpleYaml(yamlStr) {
  const data = {};
  let currentObj = null;
  let currentKey = null;
  let inList = false;
  let listItems = [];

  const lines = yamlStr.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '' || line.trim().startsWith('#')) continue;

    const indentMatch = line.match(/^(\s*)/);
    const indent = indentMatch ? indentMatch[1].length : 0;

    if (indent === 0) {
      if (inList && currentKey) {
        data[currentKey] = listItems;
        inList = false;
        listItems = [];
      }
      if (currentObj && currentKey) {
        data[currentKey] = currentObj;
        currentObj = null;
      }

      const m = line.match(/^(\w[\w_]*)\s*:\s*(.*)$/);
      if (m) {
        currentKey = m[1];
        const val = m[2].trim();
        if (val === '' || val === '[]' || val === '{}') {
          if (val === '[]') { data[currentKey] = []; currentKey = null; }
          else if (val === '{}') { data[currentKey] = {}; currentKey = null; }
        } else {
          data[currentKey] = parseVal(val);
          currentKey = null;
        }
      }
    } else if (indent >= 2 && currentKey) {
      const trimmed = line.trim();
      if (trimmed.startsWith('- ')) {
        if (!inList) { inList = true; listItems = []; }
        const objMatch = trimmed.match(/^-\s+(\w[\w_]*)\s*:\s*(.*)$/);
        if (objMatch) {
          const obj = {};
          obj[objMatch[1]] = parseVal(objMatch[2]);
          while (i + 1 < lines.length) {
            const nextLine = lines[i + 1];
            const nextIndent = (nextLine.match(/^(\s*)/) || ['',''])[1].length;
            if (nextIndent >= 4 && !nextLine.trim().startsWith('-')) {
              i++;
              const kv = nextLine.trim().match(/^(\w[\w_]*)\s*:\s*(.*)$/);
              if (kv) obj[kv[1]] = parseVal(kv[2]);
            } else break;
          }
          listItems.push(obj);
        } else {
          listItems.push(parseVal(trimmed.substring(2)));
        }
      } else {
        if (inList && currentKey) {
          data[currentKey] = listItems;
          inList = false;
          listItems = [];
        }
        if (!currentObj) currentObj = {};
        const kv = trimmed.match(/^(\w[\w_]*)\s*:\s*(.*)$/);
        if (kv) currentObj[kv[1]] = parseVal(kv[2]);
      }
    }
  }
  if (inList && currentKey) data[currentKey] = listItems;
  else if (currentObj && currentKey) data[currentKey] = currentObj;

  return data;
}

function parseVal(str) {
  if (str === 'null' || str === '~') return null;
  if (str === 'true') return true;
  if (str === 'false') return false;
  if (str === '[]') return [];
  if (str === '{}') return {};
  if ((str.startsWith('"') && str.endsWith('"')) || (str.startsWith("'") && str.endsWith("'"))) {
    return str.slice(1, -1);
  }
  const num = Number(str);
  if (!isNaN(num) && str !== '') return num;
  return str;
}

/**
 * Cache em memoria (sessionStorage) para evitar chamadas repetidas
 */
const CACHE_KEY = 'editais_cache';
const CACHE_TTL = 60000; // 1 minuto

function getCachedEditais() {
  try {
    const cached = sessionStorage.getItem(CACHE_KEY);
    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp < CACHE_TTL) return data;
    }
  } catch {}
  return null;
}

function setCachedEditais(data) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ data, timestamp: Date.now() }));
  } catch {}
}

export function invalidateCache() {
  try { sessionStorage.removeItem(CACHE_KEY); } catch {}
}

/**
 * Lista todos os editais do repositorio (retorna array de frontmatter parseado)
 */
export async function listEditais() {
  const cached = getCachedEditais();
  if (cached) return cached;

  const token = getToken();
  const headers = token ? { 'Authorization': `token ${token}` } : {};

  // Listar arquivos na pasta content/editais
  const url = `https://api.github.com/repos/${REPO_CONFIG.owner}/${REPO_CONFIG.repo}/contents/${REPO_CONFIG.contentPath}?ref=${REPO_CONFIG.branch}`;
  const resp = await fetch(url, { headers });
  if (!resp.ok) throw new Error(`Falha ao listar editais: ${resp.status}`);

  const files = await resp.json();
  const mdFiles = files.filter(f => f.name.endsWith('.md') && !f.name.startsWith('_'));

  // Buscar cada arquivo em paralelo
  const editais = await Promise.all(mdFiles.map(async (file) => {
    try {
      const fileResp = await fetch(file.url, { headers });
      if (!fileResp.ok) return null;
      const fileData = await fileResp.json();
      const content = decodeBase64UTF8(fileData.content);
      const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
      if (!match) return null;
      const frontmatter = parseSimpleYaml(match[1]);
      if (!frontmatter.id) return null;
      return { ...frontmatter, _body: match[2], _sha: fileData.sha };
    } catch {
      return null;
    }
  }));

  const result = editais.filter(Boolean);
  setCachedEditais(result);
  return result;
}

/**
 * Busca um edital especifico pelo ID
 */
export async function getEdital(id) {
  const token = getToken();
  const headers = token ? { 'Authorization': `token ${token}` } : {};

  const url = `https://api.github.com/repos/${REPO_CONFIG.owner}/${REPO_CONFIG.repo}/contents/${REPO_CONFIG.contentPath}/${id}.md?ref=${REPO_CONFIG.branch}`;
  const resp = await fetch(url, { headers });
  if (!resp.ok) throw new Error(`Edital nao encontrado: ${id}`);

  const fileData = await resp.json();
  const content = decodeBase64UTF8(fileData.content);
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) throw new Error('Formato invalido');

  const frontmatter = parseSimpleYaml(match[1]);
  return { ...frontmatter, _body: match[2], _sha: fileData.sha };
}

/**
 * Deleta um edital (md + pdf)
 */
export async function deleteEdital(id, arquivo) {
  const token = getToken();
  if (!token) throw new Error('Token nao configurado');

  await deleteFile(`${REPO_CONFIG.contentPath}/${id}.md`, token);
  if (arquivo) {
    try { await deleteFile(`editais/${arquivo}`, token); } catch {}
  }
  invalidateCache();
}

async function deleteFile(path, token) {
  const url = `https://api.github.com/repos/${REPO_CONFIG.owner}/${REPO_CONFIG.repo}/contents/${path}`;
  const getResp = await fetch(url, { headers: { 'Authorization': `token ${token}` } });
  if (!getResp.ok) throw new Error(`Arquivo nao encontrado: ${path}`);
  const fileData = await getResp.json();

  const delResp = await fetch(url, {
    method: 'DELETE',
    headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: `Excluir: ${path}`,
      sha: fileData.sha,
      branch: REPO_CONFIG.branch,
    }),
  });
  if (!delResp.ok) {
    const err = await delResp.json();
    throw new Error(err.message || `Falha ao deletar ${path}`);
  }
}

/**
 * Formata valor monetario
 */
export function formatMoney(value) {
  if (!value && value !== 0) return '—';
  return `R$ ${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}
