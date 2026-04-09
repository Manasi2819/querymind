import { useEffect, useState, useRef } from 'react'
import { getFiles, uploadFile, deleteFile } from '../api/client'

const DOC_TYPES = ['pdf', 'docx', 'txt']
const KB_TYPES = ['sql', 'json', 'md', 'csv']

export default function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState('upload') // 'upload' | 'particles'
  const [category, setCategory] = useState('document')
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [files, setFiles] = useState([])
  const [filesLoading, setFilesLoading] = useState(false)
  const [toDelete, setToDelete] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteMsg, setDeleteMsg] = useState('')
  const fileInputRef = useRef()

  const acceptedTypes = (category === 'document' ? DOC_TYPES : KB_TYPES).join(',.')

  const loadFiles = async () => {
    setFilesLoading(true)
    try {
      const data = await getFiles()
      setFiles(data)
      if (data.length > 0) setToDelete(data[0].filename)
    } catch {
      setFiles([])
    } finally {
      setFilesLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'particles') loadFiles()
  }, [activeTab])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (f) setFile(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadMsg(null)
    try {
      const data = await uploadFile(file, category)
      const chunks = data.chunks || 0
      setUploadMsg({
        type: 'success',
        text: `✅ Success: File "${file.name}" has been indexed into ${chunks} chunks. Available in Managed Particles.`,
      })
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (e) {
      setUploadMsg({
        type: 'error',
        text: e?.response?.data?.detail || '❌ Upload failed. Please try again.',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!toDelete) return
    setDeleting(true)
    setDeleteMsg('')
    try {
      await deleteFile(toDelete)
      setDeleteMsg(`Deleted "${toDelete}" successfully.`)
      await loadFiles()
    } catch {
      setDeleteMsg('Failed to delete file.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Knowledge Management</h1>
        <p className="page-subtitle">Manage the documents and metadata that power your chatbot&apos;s intelligence.</p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          id="tab-upload"
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          📤 Upload New
        </button>
        <button
          id="tab-particles"
          className={`tab-btn ${activeTab === 'particles' ? 'active' : ''}`}
          onClick={() => setActiveTab('particles')}
        >
          📦 Managed Particles
        </button>
      </div>

      {/* ── Upload Tab ── */}
      {activeTab === 'upload' && (
        <div>
          <div className="section-title">Ingest Data</div>

          {uploadMsg && (
            <div className={`alert alert-${uploadMsg.type === 'success' ? 'success' : 'error'}`}>
              <span className="alert-icon">{uploadMsg.type === 'success' ? '✅' : '⚠️'}</span>
              <span>{uploadMsg.text}</span>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: 20, alignItems: 'start' }}>
            <div>
              {/* Category */}
              <div className="form-group">
                <label className="form-label">
                  Knowledge Category
                  <span
                    title="Knowledge Base files are prioritized for schema-related questions."
                    style={{ marginLeft: 6, cursor: 'help', color: 'var(--text-muted)' }}
                  >ⓘ</span>
                </label>
                <div className="radio-group">
                  {[
                    { val: 'document', label: '📖 General Document', desc: 'PDF, Word, TXT files' },
                    { val: 'knowledge_base', label: '🧠 DB Knowledge Base', desc: 'SQL, JSON, MD, CSV — prioritized for schema queries' },
                  ].map((opt) => (
                    <label
                      key={opt.val}
                      className={`radio-option ${category === opt.val ? 'selected' : ''}`}
                    >
                      <input
                        type="radio"
                        name="category"
                        value={opt.val}
                        checked={category === opt.val}
                        onChange={() => { setCategory(opt.val); setFile(null) }}
                      />
                      <div>
                        <span className="radio-label">{opt.label}</span>
                        <span className="radio-desc">{opt.desc}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Drop Zone */}
              <div
                id="file-drop-zone"
                className={`drop-zone ${dragging ? 'dragging' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={`.${acceptedTypes}`}
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <div className="drop-zone-icon">☁️</div>
                {file ? (
                  <>
                    <div className="drop-zone-title">📄 {file.name}</div>
                    <div className="drop-zone-sub">{(file.size / 1024).toFixed(1)} KB • Click to change</div>
                  </>
                ) : (
                  <>
                    <div className="drop-zone-title">Drag and drop file here</div>
                    <div className="drop-zone-sub">
                      Limit 200MB per file • {category === 'document' ? 'PDF, DOCX, TXT' : 'SQL, JSON, MD, CSV'}
                    </div>
                  </>
                )}
              </div>

              <button
                id="upload-index-btn"
                className="btn btn-primary"
                style={{ marginTop: 14 }}
                onClick={handleUpload}
                disabled={!file || uploading}
              >
                {uploading ? <><span className="spinner" /> Processing...</> : '⬆️ Upload & Index'}
              </button>
            </div>

            {/* Support Card */}
            <div className="support-card">
              <h4>📋 Supported Formats</h4>
              <div className="support-item">
                <strong>Docs:</strong> PDF, Word (.docx), TXT
              </div>
              <div className="support-item">
                <strong>KB:</strong> SQL, JSON, MD, CSV
              </div>
              <hr className="form-divider" style={{ margin: '12px 0' }} />
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Knowledge Base files are prioritized for schema-related questions and SQL generation.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Particles Tab ── */}
      {activeTab === 'particles' && (
        <div>
          <div className="section-title">Your Knowledge Store</div>

          {deleteMsg && (
            <div className="alert alert-info" style={{ marginBottom: 16 }}>
              <span className="alert-icon">ℹ️</span>
              <span>{deleteMsg}</span>
            </div>
          )}

          {filesLoading ? (
            <div className="flex-center" style={{ padding: '40px 0' }}>
              <span className="spinner spinner-lg" />
            </div>
          ) : files.length === 0 ? (
            <div className="alert alert-info">
              <span className="alert-icon">ℹ️</span>
              <span>No knowledge particles indexed yet. Go to &quot;Upload New&quot; to get started.</span>
            </div>
          ) : (
            <>
              <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>Type</th>
                      <th>Upload Date</th>
                      <th>Chunks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((f, i) => (
                      <tr key={i}>
                        <td>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                            <span>{f.file_type === 'document' ? '📄' : '🧠'}</span>
                            <span>{f.filename}</span>
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${f.file_type === 'document' ? 'badge-blue' : 'badge-purple'}`}>
                            {f.file_type}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>
                          {f.upload_date ? new Date(f.upload_date).toLocaleDateString() : '—'}
                        </td>
                        <td>
                          <span className="badge badge-gray">{f.chunk_count} chunks</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <hr className="section-divider" />

              <div className="section-title" style={{ fontSize: 13 }}>🗑️ Remove Particle</div>
              <div className="flex" style={{ gap: 12, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ marginBottom: 0, flex: 1 }}>
                  <label className="form-label" htmlFor="delete-select">Select particle to remove</label>
                  <select
                    id="delete-select"
                    className="form-select"
                    value={toDelete}
                    onChange={(e) => setToDelete(e.target.value)}
                  >
                    {files.map((f) => (
                      <option key={f.filename} value={f.filename}>{f.filename}</option>
                    ))}
                  </select>
                </div>
                <button
                  id="delete-particle-btn"
                  className="btn btn-danger"
                  onClick={handleDelete}
                  disabled={deleting || !toDelete}
                >
                  {deleting ? <><span className="spinner" /> Deleting...</> : `🗑️ Delete`}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
