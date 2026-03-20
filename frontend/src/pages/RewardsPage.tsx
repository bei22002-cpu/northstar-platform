import React, { useEffect, useState } from 'react';
import {
  getRewardBalance,
  getRewardTransactions,
  getLeaderboard,
  getRevenueModels,
  RewardBalance,
  RewardTxn,
} from '../services/api';

export function RewardsPage() {
  const [balance, setBalance] = useState<RewardBalance | null>(null);
  const [transactions, setTransactions] = useState<RewardTxn[]>([]);
  const [leaderboard, setLeaderboard] = useState<RewardBalance[]>([]);
  const [revenueModels, setRevenueModels] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'leaderboard' | 'revenue'>('overview');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [bal, txns, lb, rev] = await Promise.all([
        getRewardBalance(1).catch(() => null),
        getRewardTransactions(1).catch(() => []),
        getLeaderboard().catch(() => []),
        getRevenueModels().catch(() => null),
      ]);
      setBalance(bal);
      setTransactions(txns);
      setLeaderboard(lb);
      setRevenueModels(rev);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const tierColor = (tier: string) => {
    const colors: Record<string, string> = {
      bronze: '#cd7f32',
      silver: '#c0c0c0',
      gold: '#ffd700',
      platinum: '#e5e4e2',
    };
    return colors[tier] || '#718096';
  };

  const rewardTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      signup_bonus: 'Sign-up Bonus',
      idea_submission: 'Idea Submission',
      feedback_provided: 'Feedback',
      referral: 'Referral',
      subscription: 'Subscription',
      engagement: 'Engagement',
      milestone: 'Milestone',
    };
    return labels[type] || type;
  };

  if (loading) {
    return (
      <div style={{ padding: '16px 16px 32px', maxWidth: 960, margin: '0 auto' }}>
        <p style={{ color: '#718096' }}>Loading rewards...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px 16px 32px', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ margin: '0 0 16px', color: '#2d3748', fontSize: 22 }}>Rewards & Engagement</h2>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 24, borderBottom: '2px solid #e2e8f0', overflowX: 'auto' }}>
        {(['overview', 'history', 'leaderboard', 'revenue'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 16px',
              border: 'none',
              background: 'transparent',
              color: activeTab === tab ? '#3182ce' : '#718096',
              fontWeight: 600,
              fontSize: 14,
              cursor: 'pointer',
              borderBottom: activeTab === tab ? '2px solid #3182ce' : '2px solid transparent',
              marginBottom: -2,
              whiteSpace: 'nowrap',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <>
          {balance ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
              <div style={summaryCard}>
                <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Token Balance</div>
                <div style={{ fontSize: 26, fontWeight: 700, color: '#2d3748' }}>
                  {balance.total_tokens.toLocaleString()}
                </div>
              </div>
              <div style={summaryCard}>
                <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Lifetime Earned</div>
                <div style={{ fontSize: 26, fontWeight: 700, color: '#2f855a' }}>
                  {balance.lifetime_earned.toLocaleString()}
                </div>
              </div>
              <div style={summaryCard}>
                <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Lifetime Spent</div>
                <div style={{ fontSize: 26, fontWeight: 700, color: '#e53e3e' }}>
                  {balance.lifetime_spent.toLocaleString()}
                </div>
              </div>
              <div style={{
                ...summaryCard,
                borderTop: `3px solid ${tierColor(balance.tier)}`,
              }}>
                <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Tier</div>
                <div style={{
                  fontSize: 26, fontWeight: 700,
                  color: tierColor(balance.tier),
                  textTransform: 'uppercase',
                }}>
                  {balance.tier}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
              <p style={{ color: '#718096', margin: 0, fontSize: 16 }}>
                No reward balance yet. Start engaging to earn tokens!
              </p>
            </div>
          )}

          {/* How to earn tokens */}
          <div style={cardStyle}>
            <h3 style={{ margin: '0 0 16px', color: '#2d3748', fontSize: 16 }}>How to Earn Tokens</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              {[
                { action: 'Sign Up', tokens: 100, desc: 'Create your account' },
                { action: 'Submit an Idea', tokens: 25, desc: 'Share a business idea for analysis' },
                { action: 'Provide Feedback', tokens: 10, desc: 'Rate AI-generated strategies' },
                { action: 'Refer a Friend', tokens: 50, desc: 'Invite others to join' },
                { action: 'Subscribe', tokens: 200, desc: 'Upgrade to a premium plan' },
                { action: 'Daily Engagement', tokens: 5, desc: 'Use the platform daily' },
              ].map((item) => (
                <div key={item.action} style={{
                  background: '#f7fafc', padding: 16, borderRadius: 8,
                  display: 'flex', flexDirection: 'column', gap: 4,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ color: '#2d3748', fontSize: 14 }}>{item.action}</strong>
                    <span style={{
                      background: '#3182ce', color: '#fff',
                      padding: '2px 8px', borderRadius: 12, fontSize: 12, fontWeight: 600,
                    }}>
                      +{item.tokens}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, color: '#718096' }}>{item.desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tier thresholds */}
          <div style={{ ...cardStyle, marginTop: 16 }}>
            <h3 style={{ margin: '0 0 16px', color: '#2d3748', fontSize: 16 }}>Tier Levels</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
              {[
                { tier: 'Bronze', threshold: 0, perks: 'Basic access' },
                { tier: 'Silver', threshold: 500, perks: 'Priority support' },
                { tier: 'Gold', threshold: 2000, perks: 'Advanced analytics' },
                { tier: 'Platinum', threshold: 10000, perks: 'All premium features' },
              ].map((t) => (
                <div key={t.tier} style={{
                  background: '#f7fafc', padding: 16, borderRadius: 8,
                  borderTop: `3px solid ${tierColor(t.tier.toLowerCase())}`,
                  textAlign: 'center',
                }}>
                  <div style={{ fontWeight: 700, color: tierColor(t.tier.toLowerCase()), fontSize: 16 }}>
                    {t.tier}
                  </div>
                  <div style={{ fontSize: 12, color: '#718096', margin: '4px 0' }}>{t.threshold.toLocaleString()} tokens</div>
                  <div style={{ fontSize: 11, color: '#4a5568' }}>{t.perks}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'history' && (
        <>
          {transactions.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
              <p style={{ color: '#718096', margin: 0 }}>No transactions yet.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 10, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
                <thead>
                  <tr style={{ background: '#edf2f7' }}>
                    {['Date', 'Type', 'Description', 'Tokens'].map((h) => (
                      <th key={h} style={thStyle}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn) => (
                    <tr key={txn.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={tdStyle}>{new Date(txn.created_at).toLocaleDateString()}</td>
                      <td style={tdStyle}>
                        <span style={{
                          background: '#edf2f7', padding: '2px 8px',
                          borderRadius: 10, fontSize: 12, fontWeight: 600,
                        }}>
                          {rewardTypeLabel(txn.reward_type)}
                        </span>
                      </td>
                      <td style={tdStyle}>{txn.description}</td>
                      <td style={{
                        ...tdStyle,
                        fontWeight: 600,
                        color: txn.tokens_earned >= 0 ? '#2f855a' : '#e53e3e',
                      }}>
                        {txn.tokens_earned >= 0 ? '+' : ''}{txn.tokens_earned}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {activeTab === 'leaderboard' && (
        <>
          {leaderboard.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
              <p style={{ color: '#718096', margin: 0 }}>No leaderboard data yet.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {leaderboard.map((user, index) => (
                <div key={user.id} style={{
                  ...cardStyle,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  marginBottom: 0,
                  borderLeft: `4px solid ${tierColor(user.tier)}`,
                }}>
                  <div style={{
                    width: 36, height: 36,
                    borderRadius: '50%',
                    background: index < 3 ? '#ffd700' : '#e2e8f0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 14, color: index < 3 ? '#744210' : '#718096',
                    flexShrink: 0,
                  }}>
                    #{index + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: '#2d3748', fontSize: 14 }}>User #{user.user_id}</div>
                    <div style={{ fontSize: 12, color: '#718096' }}>
                      Tier: <span style={{ color: tierColor(user.tier), fontWeight: 600, textTransform: 'uppercase' }}>{user.tier}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontWeight: 700, color: '#2d3748', fontSize: 16 }}>
                      {user.lifetime_earned.toLocaleString()}
                    </div>
                    <div style={{ fontSize: 11, color: '#718096' }}>tokens earned</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'revenue' && revenueModels && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {Object.entries(revenueModels).map(([key, model]) => {
            const m = model as Record<string, unknown>;
            return (
              <div key={key} style={cardStyle}>
                <h3 style={{ margin: '0 0 4px', color: '#2d3748', fontSize: 16 }}>
                  {m.name as string}
                </h3>
                <p style={{ margin: '0 0 12px', fontSize: 13, color: '#718096' }}>
                  {m.description as string}
                </p>

                {m.tiers && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                    {(m.tiers as Array<{name: string; price: number; features: string[]}>).map((tier) => (
                      <div key={tier.name} style={{
                        background: '#f7fafc', padding: 16, borderRadius: 8, textAlign: 'center',
                      }}>
                        <div style={{ fontWeight: 700, color: '#2d3748', fontSize: 15 }}>{tier.name}</div>
                        <div style={{ fontSize: 22, fontWeight: 700, color: '#3182ce', margin: '8px 0' }}>
                          ${tier.price}<span style={{ fontSize: 12, fontWeight: 400 }}>/mo</span>
                        </div>
                        <ul style={{ textAlign: 'left', fontSize: 12, color: '#718096', paddingLeft: 16, margin: 0 }}>
                          {tier.features.map((f, i) => (
                            <li key={i} style={{ marginBottom: 2 }}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {m.options && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
                    {(m.options as Array<{name: string; tokens: number; price: number}>).map((opt) => (
                      <div key={opt.name} style={{
                        background: '#f7fafc', padding: 16, borderRadius: 8, textAlign: 'center',
                      }}>
                        <div style={{ fontWeight: 700, color: '#2d3748' }}>{opt.name}</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#6b46c1', margin: '4px 0' }}>
                          {opt.tokens.toLocaleString()} tokens
                        </div>
                        <div style={{ fontSize: 14, color: '#3182ce', fontWeight: 600 }}>${opt.price}</div>
                      </div>
                    ))}
                  </div>
                )}

                {m.formats && (
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {(m.formats as string[]).map((f) => (
                      <span key={f} style={{
                        background: '#edf2f7', padding: '4px 12px',
                        borderRadius: 16, fontSize: 13, color: '#4a5568',
                      }}>
                        {f}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const summaryCard: React.CSSProperties = {
  background: '#fff',
  padding: 16,
  borderRadius: 10,
  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  textAlign: 'center',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  padding: 20,
  borderRadius: 10,
  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  marginBottom: 0,
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '12px 16px',
  fontSize: 13,
  fontWeight: 600,
  color: '#4a5568',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 14,
  color: '#2d3748',
};
