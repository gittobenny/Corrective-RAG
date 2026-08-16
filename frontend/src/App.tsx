import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, SubmitEvent } from 'react'
import './App.css'
import { getDocument, streamResearch, uploadSources } from './api'
import type { ConversationMessage, DocumentInfo, DocumentStatus } from './api'

type TrackedDocument = Pick<
  DocumentInfo,
  | 'document_id'
  | 'original_filename'
  | 'size'
  | 'status'
  | 'task_id'
  | 'chunks_stored'
  | 'error'
> &
  Partial<Pick<DocumentInfo, 'collection_id' | 'content_type' | 'created_at' | 'updated_at'>>

const PROCESSING_STATUSES: DocumentStatus[] = ['queued', 'extracting', 'embedding', 'storing']

function App() {
  const [requestText, setRequestText] = useState<string>('')
  const [markdown, setMarkdown] = useState<string>('')
  const [isResearching, setIsResearching] = useState<boolean>(false)
  const [researchError, setResearchError] = useState<string | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState<boolean>(false)
  const [uploadedDocuments, setUploadedDocuments] = useState<TrackedDocument[]>([])
  const [statusError, setStatusError] = useState<string | null>(null)
  const [conversation, setConversation] = useState<ConversationMessage[]>([])

  const abortControllerRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const userAbortRequestedRef = useRef(false)

  const selectedFileArray = Array.from({ length: selectedFiles?.length ?? 0 }, (_, index) =>
    selectedFiles?.item(index),
  ).filter((file): file is File => file !== null && file !== undefined)
  const trimmedRequest = requestText.trim()
  const pendingDocumentIds = uploadedDocuments
    .filter((document) => PROCESSING_STATUSES.includes(document.status))
    .map((document) => document.document_id)
  const pendingDocumentKey = pendingDocumentIds.join(',')
  const hasPendingDocuments = pendingDocumentIds.length > 0
  const allDocumentsReady =
    uploadedDocuments.length > 0 &&
    uploadedDocuments.every((document) => document.status === 'ready')

  useEffect(() => {
    if (!pendingDocumentKey) {
      return
    }

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const documentIds = pendingDocumentKey.split(',')

    async function pollStatuses() {
      const results = await Promise.allSettled(documentIds.map((id) => getDocument(id)))

      if (cancelled) {
        return
      }

      const updates = new Map<string, DocumentInfo>()
      let failedRequests = 0
      for (const result of results) {
        if (result.status === 'fulfilled') {
          updates.set(result.value.document_id, result.value)
        } else {
          failedRequests += 1
        }
      }

      if (updates.size > 0) {
        setUploadedDocuments((current) =>
          current.map((document) => updates.get(document.document_id) ?? document),
        )
      }
      setStatusError(
        failedRequests > 0
          ? `Could not refresh ${failedRequests} document status request(s). Retrying...`
          : null,
      )
      timer = setTimeout(pollStatuses, 2000)
    }

    void pollStatuses()

    return () => {
      cancelled = true
      if (timer) {
        clearTimeout(timer)
      }
    }
  }, [pendingDocumentKey])

  useEffect(() => {
    if (!allDocumentsReady) {
      return
    }

    const timer = setTimeout(() => {
      setUploadedDocuments([])
      setSelectedFiles(null)
      setUploadMessage(null)
      setStatusError(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }, 2000)

    return () => clearTimeout(timer)
  }, [allDocumentsReady])

  async function handleResearchSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!trimmedRequest || isResearching || hasPendingDocuments) {
      return
    }

    const abortController = new AbortController()
    abortControllerRef.current = abortController
    userAbortRequestedRef.current = false
    setMarkdown('')
    setResearchError(null)
    setIsResearching(true)
    const historyForRequest = conversation.slice(-6)
    let completedAnswer = ''

    try {
      await streamResearch(
        trimmedRequest,
        historyForRequest,
        (chunk) => {
          completedAnswer += chunk
          setMarkdown((current) => current + chunk)
        },
        abortController.signal,
      )
      setConversation((current) => {
        const additions: ConversationMessage[] = [
          { role: 'user', content: trimmedRequest },
          { role: 'assistant', content: completedAnswer.slice(0, 8_000) },
        ]
        return [
          ...current,
          ...additions,
        ].slice(-6)
      })
      setRequestText('')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        if (userAbortRequestedRef.current) {
          setResearchError('Research request cancelled.')
        }
      } else if (error instanceof Error) {
        setResearchError(error.message)
      } else {
        setResearchError('Research request failed.')
      }
    } finally {
      setIsResearching(false)
      abortControllerRef.current = null
      userAbortRequestedRef.current = false
    }
  }

  function handleAbort() {
    if (!abortControllerRef.current) {
      return
    }

    userAbortRequestedRef.current = true
    abortControllerRef.current.abort()
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = event.currentTarget.files
    setSelectedFiles(files && files.length > 0 ? files : null)
    setUploadMessage(null)
    setUploadError(null)
  }

  async function handleUploadSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFiles || selectedFiles.length === 0 || isUploading) {
      return
    }

    setIsUploading(true)
    setUploadMessage(null)
    setUploadError(null)

    try {
      const result = await uploadSources(selectedFiles)
      const uploadedNames = result.uploaded.map((file) => file.name).join(', ')
      setUploadedDocuments((current) => {
        const additions: TrackedDocument[] = result.uploaded.map((file) => ({
          document_id: file.document_id,
          original_filename: file.name,
          size: file.size,
          status: file.status,
          task_id: file.task_id,
          chunks_stored: 0,
          error: null,
          collection_id: result.collection_id,
          content_type: file.type,
        }))
        const additionIds = new Set(additions.map((document) => document.document_id))
        return [...current.filter((document) => !additionIds.has(document.document_id)), ...additions]
      })
      setUploadMessage(`Queued ${result.uploaded.length} source(s): ${uploadedNames}`)
    } catch (error) {
      if (error instanceof Error) {
        setUploadError(error.message)
      } else {
        setUploadError('Source upload failed.')
      }
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <h1 id="page-title">Research agent frontend</h1>
        <p>
          Submit a research request and upload any source files the backend should use. The
          response panel displays streamed markdown as plain source text.
        </p>
      </section>

      <section className="panel" aria-labelledby="sources-heading">
        <h2 id="sources-heading">Your sources</h2>
        <form className="form-stack" onSubmit={handleUploadSubmit}>
          <label htmlFor="source-files">Upload information sources</label>
          <input
            id="source-files"
            name="files"
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,application/pdf"
          />
          {selectedFileArray.length > 0 ? (
            <ul className="file-list" aria-label="Selected source files">
              {selectedFileArray.map((file) => (
                <li key={`${file.name}-${file.size}-${file.lastModified}`}>{file.name}</li>
              ))}
            </ul>
          ) : null}
          <div className="button-row">
            <button type="submit" disabled={isUploading || selectedFileArray.length === 0}>
              {isUploading ? 'Uploading...' : 'Upload sources'}
            </button>
          </div>
          {uploadMessage ? <p className="success">{uploadMessage}</p> : null}
          {uploadError ? <p className="error">{uploadError}</p> : null}
          {statusError ? <p className="error">{statusError}</p> : null}
          {uploadedDocuments.length > 0 ? (
            <div className="source-status" aria-live="polite">
              <h3>Document processing</h3>
              <ul>
                {uploadedDocuments.map((document) => (
                  <li key={document.document_id}>
                    <div>
                      <strong>{document.original_filename}</strong>
                      <span className={`status-badge status-${document.status}`}>
                        {document.status}
                      </span>
                    </div>
                    <small>
                      {document.status === 'ready'
                        ? `${document.chunks_stored} chunks ready for research`
                        : document.status === 'failed'
                          ? document.error || 'Processing failed'
                          : 'Processing in the background...'}
                    </small>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </form>
      </section>

      <section className="panel" aria-labelledby="request-heading">
        <h2 id="request-heading">Research request</h2>
        <form className="form-stack" onSubmit={handleResearchSubmit}>
          <label htmlFor="research-request">What should the research agent investigate?</label>
          <textarea
            id="research-request"
            name="research-request"
            rows={6}
            value={requestText}
            onChange={(event) => setRequestText(event.currentTarget.value)}
            placeholder="Type here..."
          />
          <div className="button-row">
            <button
              type="submit"
              disabled={isResearching || !trimmedRequest || hasPendingDocuments}
            >
              {isResearching ? 'Researching...' : 'Start research'}
            </button>
            {isResearching ? (
              <button type="button" className="secondary" onClick={handleAbort}>
                Abort
              </button>
            ) : null}
          </div>
          {hasPendingDocuments ? (
            <p className="processing-note">Research will be available when uploaded sources are ready.</p>
          ) : null}
          {researchError ? <p className="error">{researchError}</p> : null}
        </form>
      </section>

      <section className="panel" aria-labelledby="response-heading">
        <h2 id="response-heading">Streaming response</h2>
        <pre className="markdown-output" aria-live="polite">
          {markdown || 'Submit a research request to see the markdown answer here.'}
        </pre>
      </section>
    </main>
  )
}

export default App
