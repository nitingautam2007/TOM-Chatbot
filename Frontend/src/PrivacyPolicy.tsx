import { useEffect } from 'react';

export default function PrivacyPolicy() {
  useEffect(() => {
    document.title = 'TOM - Privacy Policy';
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-4"
      style={{
        backgroundColor: '#ffffff',
        backgroundImage:
          'linear-gradient(rgba(90,127,90,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(90,127,90,0.07) 1px, transparent 1px)',
        backgroundSize: '32px 32px',
      }}
    >
      <style>{`
        .privacy-container {
          animation: fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: scale(0.97); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>

      <div
        className="w-full max-w-2xl rounded-[2rem] overflow-hidden flex flex-col privacy-container"
        style={{
          background: 'rgba(255,255,255,0.12)',
          backdropFilter: 'blur(12px) saturate(1.4)',
          WebkitBackdropFilter: 'blur(12px) saturate(1.4)',
          border: '1px solid rgba(255,255,255,0.45)',
          boxShadow: '0 24px 60px rgba(60,90,60,0.08), 0 1.5px 0 rgba(255,255,255,0.7) inset',
        }}
      >
        {/* Header */}
        <div
          className="px-6 pt-6 pb-4 flex-shrink-0"
          style={{
            borderBottom: '1px solid rgba(90,127,90,0.1)',
            background: 'rgba(255,255,255,0.08)',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div
                className="w-11 h-11 rounded-2xl flex items-center justify-center overflow-hidden"
                style={{
                  background: '#0d0d12',
                  background: 'linear-gradient(145deg, rgba(255,255,255,0.68) 0%, rgba(255,255,255,0.42) 100%)',
                  backdropFilter: 'blur(24px) saturate(1.9)',
                  WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
                  border: '1px solid rgba(255,255,255,0.8)',
                  boxShadow: '0 8px 32px rgba(90,127,90,0.10), 0 1.5px 0 rgba(255,255,255,0.95) inset, 0 -1px 0 rgba(90,127,90,0.05) inset',
                }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7d9e7d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <div>
                <h1
                  className="text-sage-800 leading-tight"
                  style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 500, letterSpacing: '-0.01em' }}
                >
                  Privacy Policy
                </h1>
                <p className="text-[11px] text-sage-400 font-light tracking-wide">TOM - Talk To Me</p>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="prose prose-sage max-w-none text-sm">
            <h2 className="text-lg font-semibold text-sage-800 mb-4">Introduction</h2>
            <p className="text-sage-600 mb-6 leading-relaxed">
              Thank you for using TOM - Talk To Me ("TOM", "we", "us", or "our"). 
              This Privacy Policy explains how we collect, use, disclose, and safeguard 
              information when you use our mental health support chatbot.
            </p>
            
            <p className="text-sage-600 mb-6 leading-relaxed">
              Data collection is optional. You can choose not to share chats and still use TOM with local fallback replies.
            </p>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Information We Collect</h2>
            
            <h3 className="text-base font-medium text-sage-700 mb-3 mt-6">Conversation Data (With Your Consent)</h3>
            <p className="text-sage-600 mb-4 leading-relaxed">
              When you <strong>explicitly opt-in</strong> to data collection, we may collect:
            </p>
            <ul className="list-disc list-inside text-sage-600 mb-4 space-y-1">
              <li>Chat Messages: The text you send to TOM and TOM's responses</li>
              <li>Mood Selections: Your selected mood (e.g., "Struggling", "Low", "Okay", "Good", "Great")</li>
              <li>Timestamps: When conversations occurred</li>
              <li>Session Identifiers: A random browser session ID</li>
              <li>Intent Classifications: How TOM categorizes your messages</li>
              <li>Risk Levels: Whether TOM detected high-risk content</li>
            </ul>
            
            <div className="bg-sage-50 border border-sage-200 rounded-lg p-4 mb-6">
              <p className="text-sage-700 mb-2"><strong>Important:</strong> TOM does not intentionally collect:</p>
              <ul className="list-disc list-inside text-sage-600 space-y-1">
                <li>Your name</li>
                <li>Your email address</li>
                <li>Your IP address</li>
                <li>Your location</li>
                <li>Any personal identifiers</li>
                <li>Browser fingerprints or device information</li>
              </ul>
            </div>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">How We Use Your Information</h2>
            
            <h3 className="text-base font-medium text-sage-700 mb-3 mt-6">With Your Consent:</h3>
            <ol className="list-decimal list-inside text-sage-600 mb-4 space-y-1">
              <li><strong>Improve TOM:</strong> Your anonymized conversations help us train and improve TOM's responses</li>
              <li><strong>Analyze Patterns:</strong> We study aggregated, anonymized data to understand common mental health concerns</li>
              <li><strong>Research:</strong> Data may be used for academic research on mental health support technologies</li>
            </ol>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Data Protection</h2>
            <p className="text-sage-600 mb-6 leading-relaxed">
              Data is stored locally in the SQLite database on the machine running the TOM backend. This version does not encrypt the database. Do not share information that you would not want stored on that machine.
            </p>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Your Rights</h2>
            <p className="text-sage-600 mb-4 leading-relaxed">
              Select <strong>Delete my stored data and choose consent again</strong> in the chat screen to permanently delete chats and the consent record associated with this browser session. The button also clears the local session ID and reopens the consent prompt.
            </p>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Crisis Situations</h2>
            <p className="text-sage-600 mb-6 leading-relaxed">
              If TOM detects that you may be in crisis or at risk of self-harm, we display crisis resource 
              information immediately and encourage you to contact emergency services. Your safety is our priority.
            </p>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Legal Disclaimer</h2>
            <div className="bg-sage-50/80 border border-sage-200 rounded-lg p-4">
              <p className="text-sage-700 mb-2">
                <strong>TOM is NOT a substitute for professional mental health care.</strong>
              </p>
              <p className="text-sage-600 mb-2">
                If you are experiencing a crisis or need immediate help, please contact:
              </p>
              <ul className="list-disc list-inside text-sage-600 space-y-1">
                <li><strong>Crisis Text Line:</strong> Text HOME to 741741 (US/UK/Canada)</li>
                <li><strong>Suicide & Crisis Lifeline:</strong> Call or text 988 (US)</li>
                <li><strong>International:</strong> Find local crisis lines at befrienders.org</li>
              </ul>
              <p className="text-sage-600 mt-4">
                TOM is provided "as is" for educational and research purposes only. 
                We do not provide medical advice, diagnosis, or treatment.
              </p>
            </div>

            <h2 className="text-lg font-semibold text-sage-800 mb-4 mt-8">Contact Us</h2>
            <p className="text-sage-600 mb-6 leading-relaxed">
              If you have any questions about this Privacy Policy or our data practices, please contact:
            </p>
            <div className="bg-sage-50 border border-sage-200 rounded-lg p-4">
              <p className="text-sage-700">
                <strong>Project Maintainer:</strong> Nitish Gautam<br/>
                <strong>Email:</strong> nitingautam2007@gmail.com<br/>
                <strong>Project URL:</strong> https://github.com/nitingautam2007/TOM-Chatbot
              </p>
            </div>

            <div className="mt-8 pt-4 border-t border-sage-200 text-center">
              <p className="text-xs text-sage-400">
                Effective Date: September 29, 2026<br/>
                Last updated: September 29, 2026
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
