import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Activity, ArrowDownToLine, ArrowUpRight, BookOpen, Check, ChevronDown, CircleHelp, FileText, Gauge, LogOut, Menu, MessageSquare, Paperclip, Plus, Search, Send, ShieldCheck, Sparkles, UploadCloud, X } from 'lucide-react'
import { api, asAnswer, getToken, pollTask, saveToken } from './api'
import type { Answer, User } from './types'

type Message = { id: string; role: 'user' | 'assistant'; text: string; answer?: Answer; pending?: boolean }
const suggestions = [
  { title: 'Analyze financial performance', prompt: "What was Tesla's Q2 2026 revenue and operating margin?", icon: Gauge },
  { title: 'Explore a company report', prompt: "What improvements were introduced in FSD v14 lite?", icon: BookOpen },
  { title: 'Connect numbers to strategy', prompt: "How do Tesla's FSD subscriptions relate to its Q2 2026 performance?", icon: Activity },
  { title: 'Summarize a document', prompt: 'Summarize the key findings from the documents I uploaded.', icon: FileText },
]
function uid() { return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }
function pretty(value: unknown) { return typeof value === 'string' ? value : JSON.stringify(value, null, 2) }

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [topK, setTopK] = useState(5)
  const [busy, setBusy] = useState(false)
  const [statusText, setStatusText] = useState('')
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'evidence' | 'files'>('evidence')
  const [mobileMenu, setMobileMenu] = useState(false)
  const [recent, setRecent] = useState<string[]>([])
  const [uploaded, setUploaded] = useState<string[]>([])
  const [uploadBusy, setUploadBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false))
    if (getToken()) api.me().then(setUser).catch(() => saveToken(null)).finally(() => setAuthChecked(true))
    else setAuthChecked(true)
  }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])
  const lastAssistant = useMemo(() => [...messages].reverse().find(m => m.role === 'assistant' && m.answer), [messages])

  async function handleAuth(e: FormEvent) {
    e.preventDefault(); setAuthError(''); setAuthBusy(true)
    try {
      if (authMode === 'register') await api.register(username.trim(), email.trim(), password)
      const loggedIn = await api.login(username.trim(), password)
      setUser(loggedIn); setPassword('')
    } catch (err) { setAuthError(err instanceof Error ? err.message : 'Authentication failed') }
    finally { setAuthBusy(false) }
  }
  function logout() { saveToken(null); setUser(null); setMessages([]); setError('') }
  function newChat() { setMessages([]); setInput(''); setError(''); setStatusText(''); setMobileMenu(false); textareaRef.current?.focus() }

  async function sendMessage(raw?: string) {
    const query = (raw ?? input).trim()
    if (!query || busy) return
    setInput(''); setError(''); setBusy(true); setStatusText('Sending question…')
    const userMsg: Message = { id: uid(), role: 'user', text: query }
    const placeholder: Message = { id: uid(), role: 'assistant', text: '', pending: true }
    setMessages(prev => [...prev, userMsg, placeholder])
    setRecent(prev => [query, ...prev.filter(item => item !== query)].slice(0, 6))
    try {
      const queued = await api.ask(query, topK)
      setStatusText('Researching with the finance agents…')
      const result = await pollTask(queued.task_id, status => setStatusText(status === 'PENDING' ? 'Waiting for a worker…' : `Research status: ${status.toLowerCase()}`))
      const answer = asAnswer(result)
      setMessages(prev => prev.map(m => m.id === placeholder.id ? { ...m, text: answer.answer || pretty(result), answer, pending: false } : m))
      setActiveTab('evidence')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong.'
      setError(message)
      setMessages(prev => prev.filter(m => m.id !== placeholder.id))
    } finally { setBusy(false); setStatusText('') }
  }
  async function uploadFiles(files: FileList | null) {
    if (!files?.length || uploadBusy) return
    const selected = Array.from(files)
    const allowed = /\.(pdf|png|jpe?g|webp|bmp|tiff?)$/i
    const invalid = selected.find(file => !allowed.test(file.name))
    if (invalid) { setError(`${invalid.name}: only PDF and image files are supported.`); return }
    const tooBig = selected.find(file => file.size > 20 * 1024 * 1024)
    if (tooBig) { setError(`${tooBig.name} is larger than the 20 MB upload limit.`); return }
    setUploadBusy(true); setError('')
    for (const file of selected) {
      try {
        setStatusText(`Uploading ${file.name}…`)
        const queued = await api.upload(file)
        setStatusText(`Processing ${file.name}…`)
        await pollTask(queued.task_id, status => setStatusText(`${file.name}: ${status.toLowerCase()}`))
        setUploaded(prev => [file.name, ...prev.filter(name => name !== file.name)])
      } catch (err) { setError(err instanceof Error ? err.message : `Could not process ${file.name}`) }
    }
    setUploadBusy(false); setStatusText('')
    if (fileRef.current) fileRef.current.value = ''
  }
  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage() }
  }

  if (!authChecked) return <div className="loading-screen"><div className="brand-mark"><Sparkles size={22}/></div><span>Preparing your workspace…</span></div>
  if (!user) return <main className="auth-page">
    <div className="auth-decoration"><div className="orb orb-one"/><div className="orb orb-two"/><div className="auth-quote"><div className="quote-icon"><Sparkles size={22}/></div><h2>Clarity behind<br/>every number.</h2><p>Bring your reports, financial data, and questions into one thoughtful research workspace.</p><div className="quote-footer"><span className="tiny-dot"/> Built for deeper research</div></div><div className="auth-grid"/></div>
    <section className="auth-panel"><div className="auth-brand"><div className="brand-mark"><Sparkles size={20}/></div><span>FinSight<span className="brand-period">.</span></span></div><div className="auth-form-wrap"><span className="eyebrow">YOUR RESEARCH WORKSPACE</span><h1>{authMode === 'login' ? 'Welcome back' : 'Create your account'}</h1><p className="auth-subtitle">{authMode === 'login' ? 'Sign in to pick up where your research left off.' : 'Set up your workspace and start exploring.'}</p>
      <form onSubmit={handleAuth} className="auth-form">
        <label>Username<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" placeholder="Your username" required minLength={2}/></label>
        {authMode === 'register' && <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" placeholder="you@company.com" required/></label>}
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} placeholder="Enter your password" required minLength={8}/></label>
        {authError && <div className="inline-error">{authError}</div>}
        <button className="primary-btn auth-submit" disabled={authBusy}>{authBusy ? 'Please wait…' : authMode === 'login' ? 'Sign in' : 'Create account'} <ArrowUpRight size={17}/></button>
      </form><div className="auth-switch">{authMode === 'login' ? 'New to FinSight?' : 'Already have an account?'} <button onClick={() => {setAuthMode(authMode === 'login' ? 'register' : 'login');setAuthError('')}}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></div>
      <div className="auth-security"><ShieldCheck size={16}/><span>Your workspace is protected with token-based authentication.</span></div></div><div className="auth-bottom">Finance research, made more considered.</div></section>
  </main>

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="sidebar-brand"><div className="brand-mark"><Sparkles size={18}/></div><span>FinSight<span className="brand-period">.</span></span><button className="icon-btn close-menu" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={18}/></button></div>
      <button className="new-chat-btn" onClick={newChat}><Plus size={17}/> New research <span>⌘ K</span></button>
      <div className="side-label">WORKSPACE</div>
      <button className="nav-item active"><MessageSquare size={17}/> Research chat</button>
      <button className="nav-item" onClick={() => {setActiveTab('files');setMobileMenu(false)}}><FileText size={17}/> Documents <span className="nav-count">{uploaded.length}</span></button>
      <div className="side-label recent-label">RECENT QUESTIONS</div>
      <div className="recent-list">{recent.length ? recent.map(q => <button key={q} className="recent-item" onClick={() => {void sendMessage(q);setMobileMenu(false)}} title={q}><MessageSquare size={14}/><span>{q}</span></button>) : <p className="empty-recent">Your recent questions<br/>will appear here.</p>}</div>
      <div className="sidebar-bottom"><div className={`api-status ${apiOnline ? 'online' : apiOnline === false ? 'offline' : ''}`}><span className="status-dot"/><span>{apiOnline ? 'API connected' : apiOnline === false ? 'API unreachable' : 'Checking API…'}</span><button onClick={() => api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false))} title="Check API connection"><Activity size={14}/></button></div><div className="profile-row"><div className="avatar">{user.username.slice(0, 1).toUpperCase()}</div><div className="profile-info"><strong>{user.username}</strong><span>{user.role || 'Researcher'}</span></div><button className="icon-btn" onClick={logout} title="Sign out"><LogOut size={16}/></button></div></div>
    </aside>
    {mobileMenu && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileMenu(false)}/>}
    <main className="main-panel"><header className="topbar"><div className="topbar-left"><button className="icon-btn mobile-menu-btn" onClick={() => setMobileMenu(true)} aria-label="Open menu"><Menu size={19}/></button><span className="crumb">Workspace</span><span className="crumb-slash">/</span><span className="crumb-current">Research chat</span></div><div className="topbar-right"><div className="model-chip"><span className="model-dot"/><span>Local AI</span><ChevronDown size={13}/></div><button className="help-btn" title="Questions are answered using your local RAG and finance workflow"><CircleHelp size={17}/><span>How it works</span></button></div></header>
      <div className="workspace">
        <section className="conversation">
          <div className="conversation-inner">
            {messages.length === 0 ? <div className="welcome">
              <div className="welcome-glyph"><Sparkles size={24}/><span className="glyph-spark">✳</span></div><div className="eyebrow">FINANCIAL INTELLIGENCE, WITH CONTEXT</div><h1>What would you like<br/>to <em>understand</em> today?</h1><p className="welcome-copy">Ask questions across your reports and financial data. FinSight brings together document evidence and structured metrics to help you see the bigger picture.</p>
              <div className="suggestion-grid">{suggestions.map(({title,prompt,icon:Icon}) => <button className="suggestion-card" key={title} onClick={() => void sendMessage(prompt)} disabled={busy}><div className="suggestion-icon"><Icon size={17}/></div><span>{title}</span><p>{prompt}</p><ArrowUpRight size={15} className="suggestion-arrow"/></button>)}</div>
              <div className="welcome-foot"><ShieldCheck size={15}/> Your questions are processed by your configured local research workflow.</div>
            </div> : <div className="message-list">{messages.map(m => <article key={m.id} className={`message ${m.role}`}><div className={`message-avatar ${m.role}`}>{m.role === 'user' ? user.username.slice(0,1).toUpperCase() : <Sparkles size={16}/>}</div><div className="message-content"><div className="message-author">{m.role === 'user' ? 'You' : 'FinSight'}{m.role === 'assistant' && m.answer?.agent && <span className="agent-pill">{m.answer.agent.replace('_',' ')}</span>}</div>{m.pending ? <div className="thinking"><span/><span/><span/> <small>Researching evidence</small></div> : m.role === 'assistant' ? <><div className="answer-text">{m.text || 'No answer text was returned.'}</div>{m.answer?.tools_used && m.answer.tools_used.length > 0 && <div className="tool-tags">{m.answer.tools_used.map(tool => <span key={tool}><Check size={11}/>{tool}</span>)}</div>}</> : <p className="user-text">{m.text}</p>}</div></article>)}{busy && <div className="status-line"><span className="pulse-dot"/>{statusText || 'Working…'}</div>}<div ref={bottomRef}/></div>}
            {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><X size={15}/></button></div>}
          </div>
          <div className="composer-wrap"><div className="composer"><textarea ref={textareaRef} rows={1} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask about a company, metric, or report…" disabled={busy} aria-label="Ask a research question"/><div className="composer-bottom"><div className="composer-tools"><button className="tool-btn" onClick={() => fileRef.current?.click()} disabled={busy || uploadBusy}><Paperclip size={15}/><span>Add documents</span></button><span className="tool-divider"/><label className="topk-control">Sources <select value={topK} onChange={e => setTopK(Number(e.target.value))} aria-label="Number of sources"><option value={3}>3</option><option value={5}>5</option><option value={10}>10</option><option value={15}>15</option></select></label></div><button className="send-btn" onClick={() => void sendMessage()} disabled={!input.trim() || busy} aria-label="Send question"><Send size={16}/></button></div></div><input ref={fileRef} className="hidden-input" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff" onChange={e => void uploadFiles(e.target.files)}/><div className="composer-disclaimer">AI-generated responses can be inaccurate. Verify important financial information against source documents.</div></div>
        </section>
        <aside className="insights-panel"><div className="insights-head"><div><span className="eyebrow">RESEARCH CONTEXT</span><h3>Evidence & sources</h3></div><span className="panel-live"><span/> LIVE</span></div><div className="tabs"><button className={activeTab === 'evidence' ? 'selected' : ''} onClick={() => setActiveTab('evidence')}><Search size={14}/> Evidence</button><button className={activeTab === 'files' ? 'selected' : ''} onClick={() => setActiveTab('files')}><FileText size={14}/> Documents <span>{uploaded.length}</span></button></div>
          {activeTab === 'evidence' ? <div className="evidence-content">{lastAssistant?.answer ? <><div className="evidence-summary"><div className="evidence-icon"><Sparkles size={16}/></div><div><strong>Latest response</strong><p>{lastAssistant.answer.agent ? `Handled by ${lastAssistant.answer.agent.replaceAll('_',' ')}.` : 'Response returned by your research workflow.'}</p></div></div>{lastAssistant.answer.sources?.length ? <><div className="section-caption">DOCUMENT SOURCES <span>{lastAssistant.answer.sources.length}</span></div>{lastAssistant.answer.sources.map((source,i) => <div className="source-card" key={i}><div className="source-card-top"><div className="source-file-icon"><FileText size={15}/></div><span>Source {i+1}</span></div><p>{pretty(source)}</p></div>)}</> : <div className="evidence-empty compact"><BookOpen size={18}/><p>No document sources were attached to this answer.</p></div>}{lastAssistant.answer.database_rows?.length ? <><div className="section-caption">STRUCTURED DATA <span>{lastAssistant.answer.database_rows.length}</span></div>{lastAssistant.answer.database_rows.map((row,i)=><div className="data-card" key={i}><pre>{pretty(row)}</pre></div>)}</> : null}{lastAssistant.answer.tools_used?.length ? <><div className="section-caption">TOOLS USED</div><div className="tool-tags side-tags">{lastAssistant.answer.tools_used.map(t=><span key={t}><Check size={11}/>{t}</span>)}</div></> : null}</> : <div className="evidence-empty"><div className="empty-art"><div><BookOpen size={24}/></div><span/><span/></div><h4>Evidence will appear here</h4><p>Ask a question to see which agents and tools were used, alongside source documents and structured financial data.</p><button onClick={() => {setActiveTab('evidence');void sendMessage("What was Tesla's Q2 2026 revenue?")}}>Try a sample question <ArrowUpRight size={14}/></button></div>}</div> : <div className="files-content"><div className="upload-drop" onClick={() => fileRef.current?.click()} role="button" tabIndex={0} onKeyDown={e => {if(e.key==='Enter')fileRef.current?.click()}}><div className="upload-icon"><UploadCloud size={21}/></div><strong>Upload research documents</strong><p>PDFs and images, up to 20 MB each</p><span className="browse-label">Browse files <ArrowUpRight size={13}/></span></div>{uploadBusy && <div className="upload-progress"><span className="pulse-dot"/>{statusText}</div>}<div className="section-caption file-caption">UPLOADED THIS SESSION <span>{uploaded.length}</span></div>{uploaded.length ? uploaded.map(name=><div className="uploaded-file" key={name}><div className="source-file-icon"><FileText size={15}/></div><div><strong>{name}</strong><span>Processed successfully</span></div><Check size={15} className="file-check"/></div>) : <div className="files-empty">No documents uploaded yet.</div>}<div className="upload-note"><ShieldCheck size={15}/><span>Files are sent to your configured backend for ingestion into the retrieval index.</span></div></div>}
          <div className="insights-bottom"><div className="privacy-icon"><ShieldCheck size={16}/></div><div><strong>Private by design</strong><p>Powered by your own configured backend and local models.</p></div></div>
        </aside>
      </div>
    </main>
  </div>
}
