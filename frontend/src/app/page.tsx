'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'

interface Message {
  type: 'progress' | 'review' | 'error'
  content: string
}

export default function Home() {
  const [prUrl, setPrUrl] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [reviewContent, setReviewContent] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prUrl.trim()) return

    setIsProcessing(true)
    setMessages([])
    setReviewContent(null)
    
    try {
      const response = await fetch('/api/review/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pr_url: prUrl.trim() }),
      })

      if (!response.ok) throw new Error('Failed to process PR')

      const reader = response.body?.getReader()
      if (!reader) throw new Error('Failed to initialize stream reader')

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')
        console.log('Received lines:', lines)

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue
          
          try {
            const jsonStr = line.slice(6)
            console.log('Processing JSON string:', jsonStr)
            
            const data = JSON.parse(jsonStr)
            console.log('Parsed data:', {
              type: data.type,
              messagePreview: data.message?.substring(0, 100),
            })

            // Check if the message contains a nested review
            if (data.type === 'progress' && data.message?.startsWith('{"type": "review"')) {
              try {
                console.log('Found nested review message')
                const nestedData = JSON.parse(data.message)
                if (nestedData.type === 'review') {
                  console.log('Processing nested review, length:', nestedData.message?.length)
                  const message = nestedData.message
                    .replace(/\\n/g, '\n')  // Fix escaped newlines
                    .replace(/\n+/g, '\n')  // Remove extra newlines
                    .replace(/- ([0-9]+\.)/g, '$1')  // Fix numbered list formatting
                    .trim()
                  
                  console.log('Processed review preview:', message.substring(0, 200))
                  setReviewContent(message)
                }
              } catch (e) {
                console.error('Error parsing nested review:', e)
              }
            }
            // Handle regular review message
            else if (data.type === 'review') {
              console.log('Processing direct review message')
              const message = data.message
                .replace(/\\n/g, '\n')
                .replace(/\n+/g, '\n')
                .replace(/- ([0-9]+\.)/g, '$1')
                .trim()
              
              console.log('Processed review preview:', message.substring(0, 200))
              setReviewContent(message)
            }
            // Handle other messages
            else if (data.type === 'progress' || data.type === 'error') {
              console.log('Adding message:', data.type, data.message)
              setMessages(prev => [...prev, { type: data.type, content: data.message }])
            }

            if (data.type === 'complete') {
              console.log('Processing complete')
              setIsProcessing(false)
            }
          } catch (e) {
            console.error('Error parsing message:', e, '\nLine:', line)
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { 
        type: 'error', 
        content: error instanceof Error ? error.message : 'An error occurred' 
      }])
      setIsProcessing(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto">
        <div className="flex flex-col min-h-screen">
          <h1 className="text-4xl font-bold p-8">PR Reviewer</h1>
          
          <div className="flex-1 flex">
            {/* Left Panel - Form and Review */}
            <div className="flex-1 p-8 max-w-4xl">
              <div className="space-y-8">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <Input
                    type="text"
                    value={prUrl}
                    onChange={(e) => setPrUrl(e.target.value)}
                    placeholder="Enter GitHub PR URL"
                    className="w-full bg-gray-800"
                  />
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={isProcessing}
                  >
                    {isProcessing ? 'Processing...' : 'Review PR'}
                  </Button>
                </form>

                {/* Review Content */}
                {reviewContent && (
                  <div className="mt-8">
                    <div className="p-6 bg-gray-800 rounded-lg shadow-lg overflow-auto">
                      <div className="prose prose-invert prose-pre:p-0 prose-headings:border-b prose-headings:border-gray-700 prose-headings:pb-2 prose-headings:mb-4 max-w-none">
                        <ReactMarkdown
                          components={{
                            code({node, inline, className, children, ...props}) {
                              const match = /language-(\w+)/.exec(className || '')
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={oneDark}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              )
                            },
                            // Style headings
                            h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-8 first:mt-0 text-white" {...props} />,
                            h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-6 text-white" {...props} />,
                            h3: ({node, ...props}) => <h3 className="text-lg font-bold mt-4 text-white" {...props} />,
                            // Style lists with proper indentation and spacing
                            ul: ({node, ...props}) => (
                              <ul className="list-disc pl-6 my-4 space-y-2 marker:text-gray-500" {...props} />
                            ),
                            ol: ({node, ...props}) => (
                              <ol className="list-decimal pl-6 my-4 space-y-2 marker:text-gray-500" {...props} />
                            ),
                            // Style paragraphs and list items
                            p: ({node, ...props}) => (
                              <p className="my-3 text-gray-300 leading-relaxed" {...props} />
                            ),
                            li: ({node, ...props}) => (
                              <li className="text-gray-300 leading-relaxed" {...props} />
                            ),
                            // Style code blocks
                            pre: ({node, ...props}) => (
                              <pre className="my-4 rounded-lg bg-gray-900 p-4" {...props} />
                            ),
                            // Style emphasis and strong text
                            em: ({node, ...props}) => (
                              <em className="text-blue-400 not-italic" {...props} />
                            ),
                            strong: ({node, ...props}) => (
                              <strong className="text-blue-300 font-semibold" {...props} />
                            ),
                          }}
                        >
                          {reviewContent}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}

                {/* Error Messages */}
                <div className="space-y-4">
                  {messages
                    .filter(msg => msg.type === 'error')
                    .map((msg, i) => (
                      <div key={i} className="p-4 bg-red-900/50 text-red-300 rounded-lg">
                        {msg.content}
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* Right Panel - Progress */}
            <div className="w-80 p-8 bg-gray-800/50">
              <div className="sticky top-8">
                <h2 className="text-xl font-bold mb-4">Progress</h2>
                <div className="space-y-2">
                  {messages
                    .filter(msg => msg.type === 'progress')
                    .map((msg, i) => (
                      <div key={i} className="flex items-center space-x-2 text-green-400">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>{msg.content}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
