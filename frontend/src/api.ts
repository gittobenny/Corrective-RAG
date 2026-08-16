const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export type DocumentStatus =
  | 'queued'
  | 'extracting'
  | 'embedding'
  | 'storing'
  | 'ready'
  | 'failed'

export type UploadedFile = {
  name: string
  size: number
  type: string
  document_id: string
  task_id: string
  status: DocumentStatus
}

export type DocumentInfo = {
  document_id: string
  collection_id: string
  original_filename: string
  content_type: string
  size: number
  status: DocumentStatus
  task_id: string | null
  chunks_stored: number
  error: string | null
  created_at: string
  updated_at: string
}

export type ConversationMessage = {
  role: 'user' | 'assistant'
  content: string
}

export async function streamResearch(
  request: string,
  history: ConversationMessage[],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request, history: history.slice(-6) }),
    signal,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Research request failed with ${response.status}`)
  }

  if (!response.body) {
    throw new Error('Research response did not include a stream.')
  }

  const decoder = new TextDecoder()
  const reader = response.body.getReader()

  while (true) {
    const { done, value } = await reader.read()

    if (done) {
      break
    }

    onChunk(decoder.decode(value, { stream: true }))
  }

  const finalChunk = decoder.decode()

  if (finalChunk) {
    onChunk(finalChunk)
  }
}

export type UploadResult = {
  uploaded: UploadedFile[]
  collection_id: string
}

export async function uploadSources(files: FileList): Promise<UploadResult> {
  const formData = new FormData()

  for (let i = 0; i < files.length; i++) {
    const file = files.item(i)

    if (file) {
      formData.append('files', file)
    }
  }

  const response = await fetch(`${API_BASE_URL}/api/sources`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Source upload failed with ${response.status}`)
  }

  return (await response.json()) as UploadResult
}

export async function getDocument(documentId: string): Promise<DocumentInfo> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`)

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Document status request failed with ${response.status}`)
  }

  return (await response.json()) as DocumentInfo
}
