import React from 'react';
import {Composition} from 'remotion';
import {TradingLedgerDemo} from './TradingLedgerDemo';
import {TradingLedgerTerminal} from './TradingLedgerTerminal';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TradingLedgerDemo"
        component={TradingLedgerDemo}
        durationInFrames={620}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="TradingLedgerTerminal"
        component={TradingLedgerTerminal}
        durationInFrames={430}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
