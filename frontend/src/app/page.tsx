'use client'

import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'https://gmbott.vercel.app'

type View = 'home' | 'running' | 'results' | 'history'

interface UnsubItem {
  email_id: string
  sender: string
  subject?: string
  status: string
  status_code?: number
  unsubscribe_url?: string
  created_at?: string
}

interface Progress {
  emails_scanned: number
  has_more: boolean
  next_page_token: string | null
}

interface RunResult {
  summary: { total: number; success: number; failed: number; skipped: number }
  results: UnsubItem[]
  progress: Progress
}

function cleanSender(raw: string) {
  const match = raw.match(/^"?([^"<]+)"?\s*</)
  return match ? match[1].trim() : raw.split('<')[0].trim()
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'success') return <span className="text-xl">✅</span>
  if (status === 'failed') return <span className="text-xl">❌</span>
  return <span className="text-xl text-gray-300">⏭</span>
}

export default function Page() {
  const [authed, setAuthed] = useState<boolean | null>(null)
  const [view, setView] = useState<View>('home')
  const [allResults, setAllResults] = useState<UnsubItem[]>([])
  const [summary, setSummary] = useState({ total: 0, success: 0, failed: 0, skipped: 0 })
  const [progress, setProgress] = useState<Progress | null>(null)
  const [totalScanned, setTotalScanned] = useState(0)
  const [history, setHistory] = useState<UnsubItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') window.history.replaceState({}, '', '/')
    fetch(`${API}/auth/status`)
      .then(r => r.json())
      .then(d => setAuthed(d.authenticated))
      .catch(() => setAuthed(false))
  }, [])

  async function runUnsubscribe() {
    setAllResults([])
    setSummary({ total: 0, success: 0, failed: 0, skipped: 0 })
    setTotalScanned(0)
    setProgress(null)
    setError(null)
    setView('running')

    let token: string | null = null
    let hasMore = true

    while (hasMore) {
      try {
        const url = `${API}/unsubscribe/run?batch_size=300${token ? `&page_token=${encodeURIComponent(token)}` : ''}`
        const r = await fetch(url)
        if (!r.ok) throw new Error('Erro ao conectar com o servidor')
        const data: RunResult = await r.json()

        setAllResults(prev => [...prev, ...data.results])
        setSummary(prev => ({
          total:   prev.total   + data.summary.total,
          success: prev.success + data.summary.success,
          failed:  prev.failed  + data.summary.failed,
          skipped: prev.skipped + data.summary.skipped,
        }))
        setTotalScanned(prev => prev + data.progress.emails_scanned)
        setProgress(data.progress)

        hasMore = data.progress.has_more
        token = data.progress.next_page_token
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Erro desconhecido')
        hasMore = false
      }
    }

    setView('results')
  }

  async function loadHistory() {
    try {
      const r = await fetch(`${API}/unsubscribe/history?limit=200`)
      const d = await r.json()
      setHistory(d.items || [])
      setView('history')
    } catch {
      setError('Não foi possível carregar o histórico')
    }
  }

  async function logout() {
    await fetch(`${API}/auth/logout`, { method: 'POST' }).catch(() => {})
    setAuthed(false)
    setView('home')
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (authed === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // ── Not logged in ─────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-indigo-700 flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm flex flex-col items-center gap-8">
          <div className="text-center">
            <div className="text-7xl mb-4">📧</div>
            <h1 className="text-3xl font-bold text-white">Email Bot</h1>
            <p className="text-blue-200 mt-2 text-sm">Automatize seu Gmail em um toque</p>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-2xl p-5 w-full text-blue-100 text-sm space-y-3">
            <div className="flex items-center gap-2"><span>🧹</span> Descadastra newsletters automaticamente</div>
            <div className="flex items-center gap-2"><span>📋</span> Histórico de tudo que foi feito</div>
            <div className="flex items-center gap-2"><span>🗑</span> Limpeza de promoções (em breve)</div>
          </div>
          <a
            href={`${API}/auth/login`}
            className="w-full bg-white text-blue-700 font-bold py-4 px-6 rounded-2xl text-center text-lg shadow-lg active:scale-95 transition-transform flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Entrar com Google
          </a>
        </div>
      </div>
    )
  }

  // ── Running ───────────────────────────────────────────────────────────────
  if (view === 'running') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-6">
        <div className="relative">
          <div className="w-24 h-24 border-4 border-blue-100 rounded-full" />
          <div className="w-24 h-24 border-4 border-blue-600 border-t-transparent rounded-full animate-spin absolute inset-0" />
          <div className="absolute inset-0 flex items-center justify-center text-3xl">🔍</div>
        </div>
        <div className="text-center">
          <p className="text-gray-700 font-bold text-xl">Varrendo sua caixa...</p>
          <p className="text-gray-400 text-sm mt-1">Automático — não feche essa tela</p>
        </div>
        {totalScanned > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 w-full max-w-xs flex flex-col gap-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">E-mails verificados</span>
              <span className="font-bold text-gray-800">{totalScanned.toLocaleString('pt-BR')}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Descadastros</span>
              <span className="font-bold text-green-600">{summary.success}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Já feitos antes</span>
              <span className="font-bold text-gray-400">{summary.skipped}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Falhas</span>
              <span className="font-bold text-red-400">{summary.failed}</span>
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── Results ───────────────────────────────────────────────────────────────
  if (view === 'results') {
    const actionable = allResults.filter(r => r.status === 'success' || r.status === 'failed')

    return (
      <div className="min-h-screen">
        <div className="max-w-lg mx-auto p-4 pb-32">
          <div className="flex items-center gap-3 py-4">
            <button onClick={() => setView('home')} className="text-blue-600 font-medium">← Voltar</button>
            <h2 className="text-lg font-bold text-gray-800">Resultado</h2>
          </div>

          {/* Progress bar */}
          <div className="bg-slate-100 rounded-2xl p-4 mb-4 flex items-center gap-4">
            <span className="text-2xl">📊</span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-700">
                {totalScanned.toLocaleString('pt-BR')} e-mails verificados
              </p>
              {progress?.has_more && (
                <p className="text-xs text-gray-400 mt-0.5">Há mais e-mails para verificar</p>
              )}
              {!progress?.has_more && (
                <p className="text-xs text-green-600 mt-0.5 font-medium">✅ Varredura completa!</p>
              )}
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="bg-green-50 border border-green-100 rounded-2xl p-4 text-center">
              <div className="text-3xl font-bold text-green-600">{summary.success}</div>
              <div className="text-xs text-green-500 mt-1 font-medium">Descadastros</div>
            </div>
            <div className="bg-slate-100 rounded-2xl p-4 text-center">
              <div className="text-3xl font-bold text-slate-400">{summary.skipped}</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">Já feitos</div>
            </div>
            <div className="bg-red-50 border border-red-100 rounded-2xl p-4 text-center">
              <div className="text-3xl font-bold text-red-400">{summary.failed}</div>
              <div className="text-xs text-red-400 mt-1 font-medium">Falhas</div>
            </div>
          </div>

          {/* List — only show actionable items */}
          {actionable.length > 0 && (
            <div className="flex flex-col gap-2">
              {actionable.map((item, i) => (
                <div
                  key={i}
                  className={`rounded-xl p-4 flex items-center gap-3 ${item.status === 'success' ? 'bg-green-50' : 'bg-red-50'}`}
                >
                  <StatusIcon status={item.status} />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800 text-sm truncate">{cleanSender(item.sender)}</p>
                    <p className="text-gray-400 text-xs truncate">{item.subject}</p>
                    {item.status === 'failed' && item.status_code ? (
                      <p className="text-xs text-red-400 mt-0.5">HTTP {item.status_code}</p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}

          {actionable.length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <div className="text-3xl mb-2">⏭</div>
              <p className="text-sm">Todos já foram descadastrados anteriormente</p>
            </div>
          )}
        </div>

      </div>
    )
  }

  // ── History ───────────────────────────────────────────────────────────────
  if (view === 'history') {
    const successes = history.filter(h => h.status === 'success')
    const failures = history.filter(h => h.status === 'failed')
    return (
      <div className="min-h-screen">
        <div className="max-w-lg mx-auto p-4 pb-10">
          <div className="flex items-center gap-3 py-4">
            <button onClick={() => setView('home')} className="text-blue-600 font-medium">← Voltar</button>
            <h2 className="text-lg font-bold text-gray-800">Histórico</h2>
            <span className="ml-auto text-xs text-gray-400">{history.length} registros</span>
          </div>
          {history.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-4xl mb-3">📭</div>
              <p>Nenhum registro ainda</p>
            </div>
          ) : (
            <>
              {successes.length > 0 && (
                <div className="mb-5">
                  <p className="text-xs font-bold text-green-600 uppercase tracking-wide mb-2 px-1">
                    ✅ Descadastros ({successes.length})
                  </p>
                  <div className="flex flex-col gap-2">
                    {successes.map((item, i) => (
                      <div key={i} className="bg-green-50 rounded-xl p-4 flex items-center gap-3">
                        <span className="text-xl">✅</span>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-800 text-sm truncate">{cleanSender(item.sender)}</p>
                          <p className="text-gray-400 text-xs">
                            {item.created_at ? new Date(item.created_at).toLocaleDateString('pt-BR') : ''}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {failures.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-red-500 uppercase tracking-wide mb-2 px-1">
                    ❌ Falhas ({failures.length})
                  </p>
                  <div className="flex flex-col gap-2">
                    {failures.map((item, i) => (
                      <div key={i} className="bg-red-50 rounded-xl p-4 flex items-center gap-3">
                        <span className="text-xl">❌</span>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-800 text-sm truncate">{cleanSender(item.sender)}</p>
                          <p className="text-gray-400 text-xs">HTTP {item.status_code}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    )
  }

  // ── Home ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      <div className="max-w-lg mx-auto p-4">
        <div className="flex items-center justify-between py-5">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📧</span>
            <h1 className="text-xl font-bold text-gray-800">Email Bot</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full font-medium">✅ Conectado</span>
            <button onClick={logout} className="text-xs text-gray-400 hover:text-gray-600">Sair</button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-100 rounded-2xl p-4 mb-4 text-red-600 text-sm flex items-center gap-2">
            <span>❌</span> {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 text-lg">✕</button>
          </div>
        )}

        <div className="bg-blue-600 rounded-3xl p-7 shadow-xl shadow-blue-200 mb-4">
          <div className="text-4xl mb-3">🧹</div>
          <h2 className="text-2xl font-bold text-white">Descadastrar</h2>
          <p className="text-blue-200 text-sm mt-1 mb-5">
            Varre promoções, atualizações e inbox — pode continuar até cobrir todos os seus e-mails
          </p>
          <button
            onClick={() => runUnsubscribe(null)}
            className="w-full bg-white text-blue-700 font-bold py-4 rounded-2xl active:scale-95 transition-transform text-base"
          >
            🚀 Iniciar varredura
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <button
            onClick={loadHistory}
            className="w-full bg-white hover:bg-gray-50 active:scale-95 border border-gray-200 rounded-2xl p-5 text-left shadow-sm transition-all"
          >
            <div className="flex items-center gap-4">
              <span className="text-3xl">📋</span>
              <div>
                <h3 className="font-bold text-gray-800">Histórico</h3>
                <p className="text-gray-400 text-sm">Todos os descadastros realizados</p>
              </div>
              <span className="ml-auto text-gray-300 text-xl">›</span>
            </div>
          </button>

          <div className="w-full bg-white border border-dashed border-gray-200 rounded-2xl p-5 opacity-40">
            <div className="flex items-center gap-4">
              <span className="text-3xl">🗑</span>
              <div>
                <h3 className="font-bold text-gray-800">Limpar Promoções</h3>
                <p className="text-gray-400 text-sm">Em breve</p>
              </div>
              <span className="ml-auto text-xs bg-gray-100 text-gray-400 px-2 py-1 rounded-full">breve</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
