import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

const BG = '#FAF9F5';
const TERM = '#1C1C19';
const TERMBORDER = 'rgba(255,255,255,0.08)';
const OFFWHITE = '#EDEAE2';
const DIM = '#8A887F';
const GREEN = '#5DCAA5';
const TEAL = '#2BB98C';
const AMBER = '#EFA13A';
const COMMENT = '#6E6C64';
const MONO = '"SF Mono", "JetBrains Mono", Menlo, Monaco, "Courier New", monospace';

const CMD = 'claude -p "log a trade: closed the AAPL position at 214"';

const Dot: React.FC<{c: string}> = ({c}) => (
  <div style={{width: 13, height: 13, borderRadius: 7, background: c}} />
);

const Line: React.FC<{o: number; children: React.ReactNode}> = ({o, children}) => (
  <div style={{opacity: o, whiteSpace: 'pre'}}>{children}</div>
);

export const TradingLedgerTerminal: React.FC = () => {
  const frame = useCurrentFrame();
  const win = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});

  const tStart = 18;
  const perChar = 1.25;
  const nChars = Math.max(0, Math.min(CMD.length, Math.floor((frame - tStart) / perChar)));
  const cmd = CMD.slice(0, nChars);
  const typing = frame > tStart && nChars < CMD.length;
  const caretCmd = typing && Math.floor(frame / 8) % 2 === 0;

  const enterFrame = tStart + CMD.length * perChar + 8;
  const running = frame > enterFrame && frame < enterFrame + 30;
  const out = (delay: number) =>
    interpolate(frame, [enterFrame + delay, enterFrame + delay + 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const promptFrame = enterFrame + 168;
  const promptShow = frame > promptFrame;
  const caretPrompt = promptShow && Math.floor(frame / 14) % 2 === 0;

  return (
    <AbsoluteFill style={{backgroundColor: BG, justifyContent: 'center', alignItems: 'center', fontFamily: MONO}}>
      <div
        style={{
          width: 1040,
          background: TERM,
          border: `1px solid ${TERMBORDER}`,
          borderRadius: 14,
          opacity: win,
          transform: `translateY(${interpolate(win, [0, 1], [12, 0])}px)`,
          overflow: 'hidden',
          boxShadow: '0 24px 70px rgba(0,0,0,0.20)',
        }}
      >
        <div style={{height: 42, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 9, borderBottom: `1px solid ${TERMBORDER}`}}>
          <Dot c="#FF5F57" />
          <Dot c="#FEBC2E" />
          <Dot c="#28C840" />
          <div style={{flex: 1, textAlign: 'center', color: DIM, fontSize: 15}}>trading-ledger — zsh</div>
        </div>

        <div style={{padding: '24px 28px', fontSize: 21, lineHeight: 1.72, minHeight: 392}}>
          <div>
            <span style={{color: GREEN}}>~/trades</span> <span style={{color: DIM}}>$</span>{' '}
            <span style={{color: OFFWHITE}}>{cmd}</span>
            {caretCmd ? <span style={{color: OFFWHITE}}>▋</span> : null}
          </div>

          {running ? (
            <div style={{color: DIM, marginTop: 8}}>
              ● running <span style={{color: TEAL}}>trading-ledger</span> skill…
            </div>
          ) : null}

          {frame > enterFrame + 28 ? (
            <div style={{marginTop: 8}}>
              <Line o={out(30)}>
                <span style={{color: TEAL}}>✓ Matched open row:</span>
                <span style={{color: '#CFCCC3'}}> AAPL · Long · 200 shares @ 210</span>
                <span style={{color: DIM}}>  (opened Jun 20)</span>
              </Line>
              <Line o={out(52)}>
                <span style={{color: DIM}}>{'  '}exit </span>
                <span style={{color: OFFWHITE}}>214</span>
                <span style={{color: DIM}}> · P&L </span>
                <span style={{color: TEAL}}>+$800</span>
                <span style={{color: DIM}}> · plan was </span>
                <span style={{color: OFFWHITE}}>“stop 204, target 214”</span>
              </Line>
              <Line o={out(78)}>
                <span style={{color: DIM}}>{'  '}execution: </span>
                <span style={{color: TEAL}}>Per plan ✓</span>
                <span style={{color: DIM}}> — exited at your own target</span>
              </Line>
              <div style={{color: AMBER, opacity: out(108), marginTop: 10}}>
                ⚠ to-confirm: exit date — today or yesterday's close?
              </div>
              <div style={{color: COMMENT, opacity: out(134), marginTop: 8}}>
                # graded against your plan, not your P&L
              </div>
            </div>
          ) : null}

          {promptShow ? (
            <div style={{marginTop: 12}}>
              <span style={{color: GREEN}}>~/trades</span> <span style={{color: DIM}}>$</span>{' '}
              {caretPrompt ? <span style={{color: OFFWHITE}}>▋</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
