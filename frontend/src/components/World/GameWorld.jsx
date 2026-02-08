import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { WORLD_ITEMS } from '../../constants';

const ITEM_COST = 25;

function getGridCellIndex(rect, clientX, clientY) {
  const { left, top, width: w, height: h } = rect;
  const x = clientX - left;
  const y = clientY - top;
  const col = Math.floor((x / w) * 5);
  const row = Math.floor((y / h) * 5);
  const colClamped = Math.max(0, Math.min(4, col));
  const rowClamped = Math.max(0, Math.min(4, row));
  const index = rowClamped * 5 + colClamped;
  return { col: colClamped, row: rowClamped, index };
}

function isInsideGrid(rect, clientX, clientY) {
  const { left, top, width: w, height: h } = rect;
  const x = clientX - left;
  const y = clientY - top;
  return x >= 0 && x <= w && y >= 0 && y <= h;
}

export default function GameWorld({ goalType, progressPercent, currency, onPlaceItem, onUpdateCurrency, onAddPoints }) {
  const [placedItems, setPlacedItems] = useState({});
  const [hoveredTile, setHoveredTile] = useState(null);
  const [snapBackKeys, setSnapBackKeys] = useState({});
  const gridRef = useRef(null);
  const lastPointerRef = useRef({ x: 0, y: 0 });
  const hoveredTileRef = useRef(null);

  const unlockedCount = Math.max(4, Math.floor(progressPercent / 4));
  const items = WORLD_ITEMS[goalType] || WORLD_ITEMS.other;
  const canAfford = currency >= ITEM_COST;

  const handleDragEnd = (e, info, item) => {
    const dropIndex = hoveredTileRef.current;
    hoveredTileRef.current = null;
    setHoveredTile(null);
    if (!gridRef.current) {
      setSnapBackKeys((prev) => ({ ...prev, [item]: (prev[item] ?? 0) + 1 }));
      return;
    }
    const rect = gridRef.current.getBoundingClientRect();
    const last = lastPointerRef.current;
    const clientX = typeof e?.clientX === 'number' ? e.clientX : (info?.point?.x ?? last.x);
    const clientY = typeof e?.clientY === 'number' ? e.clientY : (info?.point?.y ?? last.y);
    const { index } = getGridCellIndex(rect, clientX, clientY);
    const inside = isInsideGrid(rect, clientX, clientY);
    const indexToUse = dropIndex != null ? dropIndex : (inside ? index : -1);
    const validDrop =
      indexToUse >= 0 &&
      indexToUse < unlockedCount &&
      !placedItems[indexToUse] &&
      canAfford;
    if (validDrop) {
      setPlacedItems((prev) => ({ ...prev, [indexToUse]: item }));
      if (onPlaceItem) {
        onPlaceItem().catch(() => {
          setPlacedItems((prev) => {
            const next = { ...prev };
            delete next[indexToUse];
            return next;
          });
          setSnapBackKeys((prev) => ({ ...prev, [item]: (prev[item] ?? 0) + 1 }));
        });
      } else {
        onUpdateCurrency?.(-ITEM_COST);
        onAddPoints?.(25);
      }
    } else {
      setSnapBackKeys((prev) => ({ ...prev, [item]: (prev[item] ?? 0) + 1 }));
    }
  };

  const onDrag = (e, info) => {
    if (!gridRef.current) return;
    const rect = gridRef.current.getBoundingClientRect();
    const clientX = typeof e?.clientX === 'number' ? e.clientX : info?.point?.x;
    const clientY = typeof e?.clientY === 'number' ? e.clientY : info?.point?.y;
    if (clientX != null && clientY != null) lastPointerRef.current = { x: clientX, y: clientY };
    if (clientX == null || clientY == null) return;
    const { index } = getGridCellIndex(rect, clientX, clientY);
    if (isInsideGrid(rect, clientX, clientY) && index < unlockedCount && !placedItems[index]) {
      hoveredTileRef.current = index;
      setHoveredTile(index);
    } else {
      hoveredTileRef.current = null;
      setHoveredTile(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="text-center space-y-1">
        <h2 className="font-heading text-xl sm:text-2xl uppercase tracking-tighter">PopCity Builder</h2>
        <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold">Design your manifestation</p>
      </div>
      <div className="w-full max-w-[280px] sm:max-w-[320px] mx-auto">
        <div
          ref={gridRef}
          className="relative w-full aspect-square grid grid-cols-5 gap-1 sm:gap-1.5 bg-brand-mint border-2 sm:border-4 border-brand-black p-1.5 sm:p-2 rounded-2xl sm:rounded-3xl shadow-[6px_6px_0px_#1A1A1A] sm:shadow-[8px_8px_0px_#1A1A1A]"
        >
          {Array(25).fill(null).map((_, i) => (
            <div
              key={i}
              className={`relative w-full aspect-square border border-brand-black/5 flex items-center justify-center rounded-md sm:rounded-lg overflow-hidden ${
                i < unlockedCount ? (hoveredTile === i ? 'bg-brand-pink' : 'bg-white/90') : 'bg-gray-800/10 grayscale'
              }`}
            >
              <AnimatePresence>
                {placedItems[i] ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                    className="z-10 text-xl sm:text-2xl leading-none pointer-events-none"
                  >
                    {placedItems[i]}
                  </motion.span>
                ) : i < unlockedCount ? (
                  <span className="text-[10px] sm:text-xs font-mono font-bold text-gray-300">{i + 1}</span>
                ) : (
                  <span className="text-xs opacity-20">🔒</span>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
      <div className="w-full space-y-3">
        <div className="flex justify-between items-center border-b-2 border-brand-black pb-1">
          <h3 className="font-heading text-xs uppercase tracking-widest">Store</h3>
          <span className="font-mono text-[10px] text-gray-500 uppercase font-bold">25 💰 each · 1 = 25, 2 = 50</span>
        </div>
        <div className="flex flex-wrap gap-3 justify-center py-4 px-2 sm:py-5 bg-white rounded-2xl sm:rounded-3xl border-2 border-brand-black shadow-[4px_4px_0px_#1A1A1A]">
          {items.map((item) => (
            <motion.div
              key={`${item}-${snapBackKeys[item] ?? 0}`}
              drag={canAfford}
              dragMomentum={false}
              dragElastic={0}
              onDrag={(e, info) => onDrag(e, info)}
              onDragEnd={(e, info) => handleDragEnd(e, info, item)}
              whileDrag={{ scale: 1.15, zIndex: 100 }}
              className={`w-12 h-12 sm:w-14 sm:h-14 border-2 border-brand-black rounded-xl sm:rounded-2xl flex items-center justify-center text-xl sm:text-2xl shrink-0 select-none ${
                canAfford ? 'cursor-grab bg-brand-cream active:cursor-grabbing' : 'cursor-not-allowed opacity-40 grayscale pointer-events-none'
              }`}
            >
              {item}
            </motion.div>
          ))}
        </div>
      </div>
      <div className="editorial-card p-4 sm:p-5 bg-brand-lavender w-full">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="text-2xl sm:text-3xl shrink-0">🏗️</div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-black">Construction Zone</p>
            <p className="text-[11px] sm:text-xs text-brand-black/80 mt-1">Drag items to unlocked tiles. +25 XP each.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
