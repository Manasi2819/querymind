import { useEffect, useState, useRef } from 'react'
import { getFiles, uploadFile, deleteFile } from '../api/client'

const KB_TYPES = ['sql', 'json', 'csv']
const DOC_TYPES = ['pdf', 'docx', 'txt', 'md']

export default function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState('upload') // 'upload' | 'particles'
  const [uploadType, setUploadType] = useState('data_dictionary') // 'data_dictionary' | 'general_document'
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

  const acceptedTypes = (uploadType === 'data_dictionary' ? KB_TYPES : DOC_TYPES).join(',.')

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
      const data = await uploadFile(file, uploadType)
      const chunks = data.chunks || 0
      setUploadMsg({
        type: 'success',
        text: `✅ Success: File "${file.name}" has been indexed into ${chunks} chunks as ${uploadType === 'data_dictionary' ? 'Data Dictionary' : 'General Document'}.`,
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

            <div>
              {/* Type Selection */}
              <div className="section-title" style={{ marginTop: 0, fontSize: '14px', opacity: 0.8 }}>Select Upload Category</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '25px' }}>
                <div 
                  className={`card selectable-card ${uploadType === 'data_dictionary' ? 'selected' : ''}`}
                  onClick={() => { setUploadType('data_dictionary'); setFile(null); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '24px' }}>🧠</span>
                    <div>
                      <div style={{ fontWeight: 600 }}>Data Dictionary</div>
                      <div style={{ fontSize: '11px', opacity: 0.7 }}>SQL, JSON, CSV</div>
                    </div>
                  </div>
                </div>
                <div 
                  className={`card selectable-card ${uploadType === 'general_document' ? 'selected' : ''}`}
                  onClick={() => { setUploadType('general_document'); setFile(null); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '24px' }}>📄</span>
                    <div>
                      <div style={{ fontWeight: 600 }}>General Document</div>
                      <div style={{ fontSize: '11px', opacity: 0.7 }}>PDF, DOCX, TXT, MD</div>
                    </div>
                  </div>
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
                {file ? (
                  <>
                    <div className="drop-zone-title">📄 {file.name}</div>
                    <div className="drop-zone-sub">{(file.size / 1024).toFixed(1)} KB • Click to change</div>
                  </>
                ) : (
                  <>
                    <div className="drop-zone-icon">☁️</div>
                    <div className="drop-zone-title">Drag and drop file here</div>
                    <div className="drop-zone-sub">
                      Limit 200MB per file • {uploadType === 'data_dictionary' ? 'SQL, JSON, CSV' : 'PDF, DOCX, TXT, MD'}
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
                      <th>Format</th>
                      <th>Upload Date</th>
                      <th>Chunks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((f, i) => (
                      <tr key={i}>
                        <td>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                            <span>{f.file_type === 'general_document' || f.file_type === 'document' ? '📄' : '🧠'}</span>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={{ fontWeight: 500 }}>{f.filename}</span>
                              <span style={{ fontSize: '10px', opacity: 0.6 }}>{f.file_type === 'data_dictionary' || f.file_type === 'knowledge_base' ? 'Data Dictionary' : 'General Doc'}</span>
                            </div>
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${
                            ['csv', 'xlsx'].includes(f.source_type) ? 'badge-green' : 
                            ['json'].includes(f.source_type) ? 'badge-blue' : 
                            ['sql'].includes(f.source_type) ? 'badge-purple' : 
                            ['pdf'].includes(f.source_type) ? 'badge-red' : 'badge-gray'
                          }`}>
                            {f.source_type || 'unknown'}
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
