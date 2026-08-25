import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';

const BG = '#F5F4EE';
const INK = '#2A2A27';
const MUTED = '#76746C';
const CLAUDE = '#D97757';
const USERBUBBLE = '#ECEAE0';
const TEAL = '#1D9E75';
const TEAL_BG = '#E1F5EE';
const TEAL_INK = '#0F6E56';
const BLUE_BG = '#E3EDF9';
const BLUE_INK = '#1D5A96';
const AMBER = '#BA7517';
const AMBER_BG = '#FAEEDA';
const AMBER_INK = '#854F0B';
const RED = '#C24E42';
const BORDER = 'rgba(0,0,0,0.10)';
const FONT =
  'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", sans-serif';

const SENTENCE = 'bought 500 NVDA at 135, stop 128 — betting the earnings gap fills';

const ROWS = [
  {k: 'Ticker', v: 'NVDA · Long · 500 shares @ 135', tag: 'Open', tagBg: BLUE_BG, tagInk: BLUE_INK},
  {k: 'Thesis', v: 'earnings gap fills', tag: 'captured', tagBg: TEAL_BG, tagInk: TEAL_INK},
  {k: 'Plan', v: 'stop 128 · target ?', tag: null as string | null, tagBg: '', tagInk: ''},
];

const EXEC = [
  {label: 'Per plan', n: 5, color: TEAL},
  {label: 'Early exit', n: 2, color: AMBER},
  {label: 'Impulse', n: 1, color: RED},
];

const Sparkle: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="0 0 100 100" style={{display: 'block'}}>
    {Array.from({length: 12}).map((_, i) => {
      const a = (i * 30 * Math.PI) / 180;
      const x1 = 50 + Math.cos(a) * 15;
      const y1 = 50 + Math.sin(a) * 15;
      const x2 = 50 + Math.cos(a) * 47;
      const y2 = 50 + Math.sin(a) * 47;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={CLAUDE} strokeWidth={7} strokeLinecap="round" />;
    })}
  </svg>
);

const easeIn = (frame: number, fps: number, delay: number) =>
  spring({frame: frame - delay, fps, config: {damping: 200}});

export const TradingLedgerDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sceneA = interpolate(frame, [420, 458], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sceneB = interpolate(frame, [430, 468], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: BG, fontFamily: FONT}}>
      {sceneA > 0.01 ? <SceneChat frame={frame} fps={fps} opacity={sceneA} /> : null}
      {sceneB > 0.01 ? <SceneReview frame={frame} fps={fps} opacity={sceneB} /> : null}
    </AbsoluteFill>
  );
};

const SceneChat: React.FC<{frame: number; fps: number; opacity: number}> = ({frame, fps, opacity}) => {
  const headerIn = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});

  const typeStart = 20;
  const perChar = 1.4;
  const nChars = Math.max(0, Math.min(SENTENCE.length, Math.floor((frame - typeStart) / perChar)));
  const typed = SENTENCE.slice(0, nChars);
  const typing = nChars < SENTENCE.length && frame > typeStart;
  const caret = typing && Math.floor(frame / 8) % 2 === 0;
  const userIn = interpolate(frame, [typeStart - 6, typeStart + 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const replyStart = 158;
  const reply = easeIn(frame, fps, replyStart);
  const thinking = frame > 124 && frame < replyStart;

  return (
    <AbsoluteFill style={{opacity, alignItems: 'center'}}>
      <div style={{width: 880, height: '100%', display: 'flex', flexDirection: 'column', padding: '34px 0 26px'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 9, opacity: headerIn}}>
          <Sparkle size={24} />
          <span style={{fontSize: 21, color: INK, fontWeight: 500}}>Claude</span>
        </div>

        <div style={{flex: 1, paddingTop: 30}}>
          <div style={{display: 'flex', justifyContent: 'flex-end', marginBottom: 26}}>
            <div
              style={{
                maxWidth: 640,
                background: USERBUBBLE,
                color: INK,
                fontSize: 25,
                lineHeight: 1.5,
                padding: '15px 21px',
                borderRadius: 20,
                opacity: userIn,
                transform: `translateY(${interpolate(userIn, [0, 1], [10, 0])}px)`,
              }}
            >
              {typed}
              {caret ? <span style={{opacity: 0.6}}>▋</span> : null}
            </div>
          </div>

          {thinking ? (
            <div style={{display: 'flex', alignItems: 'center', gap: 13}}>
              <Sparkle size={24} />
              <Dots frame={frame} />
            </div>
          ) : null}

          {reply > 0.02 ? (
            <div style={{display: 'flex', gap: 15, opacity: reply, transform: `translateY(${interpolate(reply, [0, 1], [10, 0])}px)`}}>
              <div style={{marginTop: 2}}>
                <Sparkle size={24} />
              </div>
              <div style={{flex: 1}}>
                <div style={{fontSize: 24, color: INK, marginBottom: 16}}>Logged ✅</div>
                {ROWS.map((r, i) => (
                  <Row key={i} r={r} frame={frame} fps={fps} delay={replyStart + 24 + i * 22} />
                ))}
                <Confirm frame={frame} />
              </div>
            </div>
          ) : null}
        </div>

        <div
          style={{
            border: `1px solid ${BORDER}`,
            borderRadius: 16,
            padding: '15px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FBFAF6',
            opacity: headerIn,
          }}
        >
          <span style={{color: MUTED, fontSize: 20}}>Reply to Claude…</span>
          <div style={{width: 34, height: 34, borderRadius: 17, background: CLAUDE, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 19}}>↑</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Dots: React.FC<{frame: number}> = ({frame}) => {
  const o = (i: number) => 0.3 + 0.7 * Math.abs(Math.sin((frame - i * 4) / 6));
  return (
    <span style={{display: 'inline-flex', gap: 5}}>
      {[0, 1, 2].map((i) => (
        <span key={i} style={{width: 7, height: 7, borderRadius: 4, background: MUTED, opacity: o(i), display: 'inline-block'}} />
      ))}
    </span>
  );
};

const Row: React.FC<{r: typeof ROWS[number]; frame: number; fps: number; delay: number}> = ({r, frame, fps, delay}) => {
  const s = easeIn(frame, fps, delay);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '10px 0', opacity: s, transform: `translateX(${interpolate(s, [0, 1], [-14, 0])}px)`}}>
      <div style={{width: 9, height: 9, borderRadius: 5, background: TEAL, flexShrink: 0}} />
      <div style={{fontSize: 22, fontWeight: 500, color: INK, width: 108}}>{r.k}</div>
      <div style={{fontSize: 22, color: MUTED, flex: 1}}>{r.v}</div>
      <div style={{width: 130, textAlign: 'right'}}>
        {r.tag ? <span style={{fontSize: 17, background: r.tagBg, color: r.tagInk, padding: '4px 12px', borderRadius: 999}}>{r.tag}</span> : null}
      </div>
    </div>
  );
};

const Confirm: React.FC<{frame: number}> = ({frame}) => {
  const start = 262;
  const o = interpolate(frame, [start, start + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (o < 0.02) return null;
  return (
    <div style={{marginTop: 14, background: AMBER_BG, border: `1px solid rgba(186,117,23,0.35)`, borderRadius: 14, padding: '13px 17px', display: 'flex', gap: 11, alignItems: 'flex-start', maxWidth: 620, opacity: o, transform: `translateY(${interpolate(o, [0, 1], [6, 0])}px)`}}>
      <div style={{fontSize: 21}}>❓</div>
      <div style={{fontSize: 20, lineHeight: 1.45, color: AMBER_INK}}>
        <span style={{fontWeight: 500}}>to-confirm:</span> no target — where do you take profit? And the mood: calm, or chasing?
      </div>
    </div>
  );
};

const SceneReview: React.FC<{frame: number; fps: number; opacity: number}> = ({frame, fps, opacity}) => {
  const maxN = 5;
  const titleIn = interpolate(frame, [440, 466], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const taglineIn = interpolate(frame, [514, 546], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const urlIn = interpolate(frame, [556, 582], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{opacity, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{width: 820}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 11, marginBottom: 26, opacity: titleIn}}>
          <Sparkle size={22} />
          <span style={{fontSize: 22, color: MUTED}}>review my trades — how was the execution this month?</span>
        </div>
        <div style={{display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 44}}>
          {EXEC.map((b, i) => {
            const s = easeIn(frame, fps, 462 + i * 12);
            const w = (b.n / maxN) * 620 * s;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 18}}>
                <div style={{width: 150, fontSize: 24, color: INK, fontWeight: 500}}>{b.label}</div>
                <div style={{flex: 1, height: 26, position: 'relative'}}>
                  <div style={{height: 26, width: 620, background: 'rgba(0,0,0,0.05)', borderRadius: 999, position: 'absolute'}} />
                  <div style={{height: 26, width: w, background: b.color, borderRadius: 999, position: 'absolute'}} />
                </div>
                <div style={{width: 70, textAlign: 'right', fontSize: 22, color: MUTED, opacity: s}}>×{b.n}</div>
              </div>
            );
          })}
        </div>
        <div style={{fontSize: 32, fontWeight: 500, color: INK, lineHeight: 1.4, opacity: taglineIn, transform: `translateY(${interpolate(taglineIn, [0, 1], [10, 0])}px)`}}>
          Say your reason out loud at the moment of entry.
          <br />
          <span style={{color: CLAUDE}}>It grades your execution</span> — not your P&L.
        </div>
        <div style={{fontSize: 22, color: MUTED, marginTop: 22, opacity: urlIn}}>github.com/cruisekkk/trading-ledger</div>
      </div>
    </AbsoluteFill>
  );
};
