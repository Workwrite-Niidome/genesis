'use client'

import { useState } from 'react'
import { Lock, Unlock, Crown, Loader2 } from 'lucide-react'
import { api, REPORT_TYPES, IndividualBillingStatus } from '@/lib/api'
import Link from 'next/link'

interface CategoryReportSectionProps {
  billingStatus: IndividualBillingStatus | null
  lang: string
  residentName: string
}

function t(lang: string, ja: string, en: string): string {
  return lang === 'en' ? en : ja
}

export default function CategoryReportSection({
  billingStatus,
  lang,
  residentName,
}: CategoryReportSectionProps) {
  const [loadingReport, setLoadingReport] = useState<string | null>(null)

  const isPro = billingStatus?.plan === 'pro'
  const purchasedReports = billingStatus?.purchased_reports ?? []

  const handleReportClick = async (reportKey: string) => {
    const hasAccess = isPro || purchasedReports.includes(reportKey)

    if (hasAccess) {
      // Navigate to report page
      window.location.href = `/report/${reportKey}`
      return
    }

    // Create checkout for this report
    setLoadingReport(reportKey)
    try {
      const { checkout_url } = await api.createReportCheckout(reportKey)
      window.location.href = checkout_url
    } catch (err: any) {
      alert(err.message || 'Failed to create checkout')
    } finally {
      setLoadingReport(null)
    }
  }

  const handleProCheckout = async (planType: 'monthly' | 'annual') => {
    try {
      const { checkout_url } = await api.createIndividualCheckout(planType)
      window.location.href = checkout_url
    } catch (err: any) {
      alert(err.message || 'Failed to create checkout')
    }
  }

  return (
    <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
      {/* Section Header */}
      <div className="flex items-center gap-2 mb-4">
        <Lock size={18} className="text-accent-gold" />
        <h3 className="text-text-primary font-semibold">
          {t(lang, 'あなたの構造を深く知る', 'Discover Your Inner Structure')}
        </h3>
      </div>

      <p className="text-text-muted text-sm mb-5">
        {t(lang,
          '6つのカテゴリから、あなたの内面構造がどのように現れるかを詳しく分析します。',
          'Get detailed analysis of how your inner structure manifests across 6 categories.'
        )}
      </p>

      {/* Report Cards Grid */}
      <div className="grid grid-cols-1 min-[480px]:grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
        {REPORT_TYPES.map((report) => {
          const hasAccess = isPro || purchasedReports.includes(report.key)
          const isLoading = loadingReport === report.key
          return (
            <button
              key={report.key}
              onClick={() => handleReportClick(report.key)}
              disabled={isLoading}
              className={`relative p-4 rounded-lg border text-left transition-all ${
                hasAccess
                  ? 'border-accent-gold/30 bg-accent-gold/5 hover:bg-accent-gold/10'
                  : 'border-border-default bg-bg-primary hover:border-border-hover hover:bg-bg-hover'
              }`}
            >
              <div className="text-2xl mb-2">{report.emoji}</div>
              <p className="text-text-primary text-sm font-medium">
                {lang === 'en' ? report.en : report.ja}
              </p>
              {hasAccess ? (
                <div className="flex items-center gap-1 mt-2">
                  <Unlock size={12} className="text-accent-gold" />
                  <span className="text-accent-gold text-xs font-semibold">
                    {t(lang, '閲覧可能', 'Available')}
                  </span>
                </div>
              ) : (
                <p className="text-text-muted text-xs mt-2">
                  {isLoading ? (
                    <Loader2 size={12} className="animate-spin inline" />
                  ) : (
                    '¥300'
                  )}
                </p>
              )}
            </button>
          )
        })}
      </div>

      {/* Pro Upgrade CTA */}
      {!isPro && (
        <div className="border-t border-border-default pt-5">
          <div className="flex items-center gap-2 mb-3">
            <Crown size={18} className="text-accent-gold" />
            <h4 className="text-text-primary font-semibold text-sm">
              {t(lang, 'Proプランで全レポート見放題', 'Unlimited Reports with Pro')}
            </h4>
          </div>
          <p className="text-text-muted text-xs mb-4">
            {t(lang,
              '全6カテゴリのレポート + AIチャット無制限 + 再診断',
              'All 6 category reports + Unlimited AI Chat + Re-diagnosis'
            )}
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={() => handleProCheckout('monthly')}
              className="flex-1 px-4 py-2.5 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors text-sm"
            >
              {t(lang, '月額 ¥980 で始める', '¥980/month')}
            </button>
            <button
              onClick={() => handleProCheckout('annual')}
              className="flex-1 px-4 py-2.5 bg-bg-primary text-text-primary border border-accent-gold/40 rounded-lg hover:bg-accent-gold/10 transition-colors text-sm"
            >
              {t(lang, '年額 ¥9,800（2ヶ月無料）', '¥9,800/year (save 2 months)')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
