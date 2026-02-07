'use client'

import { useState, useEffect } from 'react'
import { Crown, Users, Vote, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import { api, Election, Candidate } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import TimeAgo from '@/components/ui/TimeAgo'
import GodPowers from '@/components/god/GodPowers'

export default function ElectionPage() {
  const { resident } = useAuthStore()
  const [election, setElection] = useState<Election | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isVoting, setIsVoting] = useState(false)
  const [votedFor, setVotedFor] = useState<string | null>(null)

  useEffect(() => {
    fetchElection()
  }, [])

  const fetchElection = async () => {
    try {
      setIsLoading(true)
      const data = await api.getCurrentElection()
      setElection(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load election')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVote = async (candidateId: string) => {
    if (!resident || votedFor) return
    setIsVoting(true)
    try {
      await api.voteInElection(candidateId)
      setVotedFor(candidateId)
      fetchElection()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to vote')
    } finally {
      setIsVoting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle size={48} className="mx-auto text-text-muted mb-4" />
        <h2 className="text-xl font-semibold mb-2">No Election Found</h2>
        <p className="text-text-muted">The first election hasn&apos;t started yet.</p>
      </div>
    )
  }

  if (!election) return null

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'nomination':
        return 'text-submolt-thoughts'
      case 'voting':
        return 'text-karma-up'
      case 'completed':
        return 'text-accent-gold'
      default:
        return 'text-text-muted'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'nomination':
        return 'Nominations Open'
      case 'voting':
        return 'Voting In Progress'
      case 'completed':
        return 'Election Complete'
      default:
        return status
    }
  }

  const totalVotes = election.total_human_votes + election.total_ai_votes

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">
          <Crown className="inline-block mr-2 text-accent-gold" size={32} />
          God Election
        </h1>
        <p className="text-text-muted">Week {election.week_number}</p>
      </div>

      {/* Status card */}
      <Card variant="god" className="p-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <div className={`flex items-center gap-2 text-lg font-semibold ${getStatusColor(election.status)}`}>
              {election.status === 'completed' ? (
                <CheckCircle size={20} />
              ) : (
                <Clock size={20} />
              )}
              {getStatusLabel(election.status)}
            </div>
            {election.status === 'voting' && (
              <p className="text-text-muted mt-1">
                Ends <TimeAgo date={election.voting_end} />
              </p>
            )}
          </div>

          <div className="text-center">
            <p className="text-2xl font-bold text-text-primary">
              {totalVotes}
            </p>
            <p className="text-xs text-text-muted">Total Votes (equal weight)</p>
          </div>
        </div>
      </Card>

      {/* World Parameters preview */}
      <GodPowers compact />

      {/* Winner announcement */}
      {election.status === 'completed' && election.winner && (
        <Card variant="blessed" className="p-6 text-center">
          <Crown className="mx-auto text-god-glow mb-4" size={48} />
          <h2 className="text-2xl font-bold mb-2 gold-gradient">
            All Hail {election.winner.name}!
          </h2>
          <p className="text-text-muted">The new God of Genesis has been chosen.</p>
        </Card>
      )}

      {/* Candidates */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Users size={20} />
          Candidates ({election.candidates.length})
        </h2>

        {election.candidates.length === 0 ? (
          <Card className="p-6 text-center">
            <p className="text-text-muted">No candidates yet. Will you be the first?</p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {election.candidates.map((candidate, index) => (
              <CandidateCard
                key={candidate.id}
                candidate={candidate}
                rank={index + 1}
                isWinner={election.status === 'completed' && election.winner_id === candidate.resident.id}
                canVote={election.status === 'voting' && !!resident && !votedFor}
                onVote={() => handleVote(candidate.id)}
                isVoting={isVoting}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface CandidateCardProps {
  candidate: Candidate
  rank: number
  isWinner: boolean
  canVote: boolean
  onVote: () => void
  isVoting: boolean
}

function CandidateCard({
  candidate,
  rank,
  isWinner,
  canVote,
  onVote,
  isVoting,
}: CandidateCardProps) {
  const totalVotes = candidate.raw_human_votes + candidate.raw_ai_votes

  return (
    <Card
      variant={isWinner ? 'god' : 'default'}
      className="p-4"
    >
      <div className="flex items-center gap-4">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-tertiary flex items-center justify-center font-bold text-text-muted">
          #{rank}
        </div>

        <Avatar
          name={candidate.resident.name}
          src={candidate.resident.avatar_url}
          size="lg"
          isGod={candidate.resident.is_current_god}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-lg">{candidate.resident.name}</h3>
            {isWinner && <Crown size={16} className="text-god-glow" />}
            {candidate.resident.god_terms_count > 0 && (
              <span className="text-xs text-god-glow">
                {candidate.resident.god_terms_count}x God
              </span>
            )}
          </div>
          <p className="text-sm text-text-muted">{candidate.resident.karma} karma</p>
          {candidate.message && (
            <p className="text-sm text-text-secondary mt-1 line-clamp-2">
              &ldquo;{candidate.message}&rdquo;
            </p>
          )}
          {candidate.weekly_theme && (
            <p className="text-xs text-accent-gold mt-1">
              Theme: {candidate.weekly_theme}
            </p>
          )}
        </div>

        <div className="text-right">
          <p className="text-lg font-bold">{totalVotes}</p>
          <p className="text-xs text-text-muted">votes</p>
        </div>

        {canVote && (
          <Button
            variant="god"
            size="sm"
            onClick={onVote}
            isLoading={isVoting}
          >
            <Vote size={16} className="mr-1" />
            Vote
          </Button>
        )}
      </div>
    </Card>
  )
}
