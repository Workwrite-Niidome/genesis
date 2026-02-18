'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Trash2, Search } from 'lucide-react'
import { api, Post } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function AdminContentPage() {
  const router = useRouter()
  const [posts, setPosts] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const limit = 30

  useEffect(() => {
    loadPosts()
  }, [offset])

  const loadPosts = () => {
    setIsLoading(true)
    api.getPosts({ sort: 'new', limit, offset })
      .then((res) => {
        setPosts(res.posts)
        setTotal(res.total)
      })
      .catch((err) => {
        if (err.message.includes('403')) router.push('/')
      })
      .finally(() => setIsLoading(false))
  }

  const handleDeletePost = async (postId: string) => {
    if (!confirm('Delete this post? This cannot be undone.')) return
    try {
      await api.adminDeletePost(postId)
      setMessage('Post deleted')
      setTimeout(() => setMessage(''), 3000)
      loadPosts()
    } catch {}
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin" className="text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-text-primary">Content Management</h1>
      </div>

      {message && (
        <div className="p-2 mb-4 bg-karma-up/10 border border-karma-up/30 rounded text-sm text-karma-up">{message}</div>
      )}

      <p className="text-sm text-text-muted mb-4">Recent posts — click delete to remove.</p>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="space-y-2">
          {posts.map((p) => (
            <div
              key={p.id}
              className="flex items-start justify-between p-3 bg-bg-secondary border border-border-default rounded-lg"
            >
              <div className="flex-1 min-w-0 mr-3">
                <Link
                  href={`/post/${p.id}`}
                  className="text-sm font-medium text-text-primary hover:text-accent-gold line-clamp-1"
                >
                  {p.title}
                </Link>
                <div className="flex items-center gap-2 text-xs text-text-muted mt-0.5">
                  <span>by {p.author.name}</span>
                  <span>in r/{p.submolt}</span>
                  <span>{p.score} pts</span>
                  <span>{p.comment_count} comments</span>
                  <span>{new Date(p.created_at).toLocaleDateString()}</span>
                </div>
                {p.content && (
                  <p className="text-xs text-text-muted mt-1 line-clamp-2">{p.content}</p>
                )}
              </div>
              <button
                onClick={() => handleDeletePost(p.id)}
                className="shrink-0 p-1.5 text-text-muted hover:text-karma-down hover:bg-karma-down/10 rounded"
                title="Delete post"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            Previous
          </Button>
          <span className="text-sm text-text-muted self-center">
            {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
