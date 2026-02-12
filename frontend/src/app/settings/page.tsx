'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { User, Shield, Save, Check } from 'lucide-react'
import { api, Resident } from '@/lib/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import RoleSelector from '@/components/profile/RoleSelector'
import { useAuthStore } from '@/stores/authStore'

type TabId = 'profile' | 'roles'

interface Tab {
  id: TabId
  name: string
  icon: React.ElementType
}

const TABS: Tab[] = [
  { id: 'profile', name: 'Profile', icon: User },
  { id: 'roles', name: 'Roles', icon: Shield },
]

export default function SettingsPage() {
  const router = useRouter()
  const { resident, setResident, isAuthenticated, isLoading: authLoading } = useAuthStore()
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Profile form state
  const [description, setDescription] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [bio, setBio] = useState('')
  const [locationDisplay, setLocationDisplay] = useState('')
  const [occupationDisplay, setOccupationDisplay] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [interestsText, setInterestsText] = useState('')

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/')
      return
    }

    if (resident) {
      setDescription(resident.description || '')
      setAvatarUrl(resident.avatar_url || '')
      setBio(resident.bio || '')
      setLocationDisplay(resident.location_display || '')
      setOccupationDisplay(resident.occupation_display || '')
      setWebsiteUrl(resident.website_url || '')
      setInterestsText((resident.interests_display || []).join(', '))
      setIsLoading(false)
    }
  }, [resident, isAuthenticated, authLoading, router])

  const handleSaveProfile = async () => {
    if (!resident) return

    setIsSaving(true)
    setSaveSuccess(false)

    const interests = interestsText
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0)
      .slice(0, 10)

    try {
      const updated = await api.updateMe({
        description: description || undefined,
        avatar_url: avatarUrl || undefined,
        bio: bio || undefined,
        location_display: locationDisplay || undefined,
        occupation_display: occupationDisplay || undefined,
        website_url: websiteUrl || undefined,
        interests_display: interests.length > 0 ? interests : undefined,
      })
      setResident(updated)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      console.error('Failed to update profile:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleRolesChange = (newRoles: string[]) => {
    if (resident) {
      setResident({ ...resident, roles: newRoles })
    }
  }

  if (authLoading || isLoading || !resident) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-genesis-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar */}
        <div className="md:w-48 shrink-0">
          <nav className="flex md:flex-col gap-1">
            {TABS.map(tab => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg text-left transition-colors
                    ${isActive
                      ? 'bg-genesis-gold/20 text-genesis-gold'
                      : 'text-genesis-secondary hover:text-genesis-primary hover:bg-genesis-tertiary'
                    }
                  `}
                >
                  <Icon size={18} />
                  <span className="text-sm font-medium">{tab.name}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-6">Profile Settings</h2>

              <div className="space-y-6">
                {/* Avatar preview */}
                <div className="flex items-center gap-4">
                  <Avatar
                    name={resident.name}
                    src={avatarUrl || resident.avatar_url}
                    size="lg"
                    className="w-20 h-20"
                  />
                  <div>
                    <p className="font-medium">{resident.name}</p>
                  </div>
                </div>

                {/* Avatar URL */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    Avatar URL
                  </label>
                  <input
                    type="url"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://example.com/avatar.png"
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold"
                  />
                  <p className="mt-1 text-xs text-genesis-muted">
                    Enter an image URL
                  </p>
                </div>

                {/* Bio */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    Bio
                  </label>
                  <textarea
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="Tell us about yourself..."
                    rows={3}
                    maxLength={2000}
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold resize-none"
                  />
                  <p className="mt-1 text-xs text-genesis-muted text-right">
                    {bio.length}/2000
                  </p>
                </div>

                {/* Occupation */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    What you do
                  </label>
                  <input
                    type="text"
                    value={occupationDisplay}
                    onChange={(e) => setOccupationDisplay(e.target.value)}
                    placeholder="e.g. barista, freelance designer, student"
                    maxLength={100}
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold"
                  />
                </div>

                {/* Location */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    Location
                  </label>
                  <input
                    type="text"
                    value={locationDisplay}
                    onChange={(e) => setLocationDisplay(e.target.value)}
                    placeholder="e.g. Tokyo, Portland OR, the void"
                    maxLength={100}
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold"
                  />
                </div>

                {/* Website */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    Website
                  </label>
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://your-site.com"
                    maxLength={200}
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold"
                  />
                </div>

                {/* Interests */}
                <div>
                  <label className="block text-sm font-medium text-genesis-secondary mb-2">
                    Interests
                  </label>
                  <input
                    type="text"
                    value={interestsText}
                    onChange={(e) => setInterestsText(e.target.value)}
                    placeholder="gaming, music, cooking (comma-separated)"
                    className="w-full px-4 py-2 bg-genesis-tertiary border border-genesis-border rounded-lg text-genesis-primary placeholder-genesis-muted focus:outline-none focus:border-genesis-gold"
                  />
                  <p className="mt-1 text-xs text-genesis-muted">
                    Comma-separated, up to 10 tags
                  </p>
                </div>

                {/* Save button */}
                <div className="flex justify-end">
                  <Button
                    onClick={handleSaveProfile}
                    disabled={isSaving}
                  >
                    {isSaving ? (
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : saveSuccess ? (
                      <>
                        <Check size={16} />
                        Saved
                      </>
                    ) : (
                      <>
                        <Save size={16} />
                        Save
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'roles' && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-2">Role Settings</h2>
              <p className="text-sm text-genesis-muted mb-6">
                Roles express your playstyle and identity. They help other residents find you.
              </p>

              <RoleSelector
                currentRoles={resident.roles}
                onRolesChange={handleRolesChange}
              />
            </Card>
          )}

        </div>
      </div>
    </div>
  )
}
