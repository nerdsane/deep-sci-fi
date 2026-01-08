/**
 * ContextMenu - Right-click contextual actions for elements
 */
import React, { useEffect, useRef, useState, useLayoutEffect } from 'react';

export interface ContextMenuItem {
  id: string;
  label: string;
  icon?: string;
  shortcut?: string;
  disabled?: boolean;
  danger?: boolean;
  separator?: boolean;
}

export interface ContextMenuProps {
  items: ContextMenuItem[];
  position: { x: number; y: number };
  onSelect: (itemId: string) => void;
  onClose: () => void;
}

export function ContextMenu({ items, position, onSelect, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPosition, setAdjustedPosition] = useState(position);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // Adjust position to stay within viewport - use useLayoutEffect to avoid flash
  useLayoutEffect(() => {
    if (!menuRef.current) return;

    const rect = menuRef.current.getBoundingClientRect();
    let x = position.x;
    let y = position.y;

    // Only adjust if menu would be cut off
    if (x + rect.width > window.innerWidth - 8) {
      x = window.innerWidth - rect.width - 8;
    }
    if (y + rect.height > window.innerHeight - 8) {
      y = window.innerHeight - rect.height - 8;
    }

    // Ensure not negative
    x = Math.max(8, x);
    y = Math.max(8, y);

    setAdjustedPosition({ x, y });
  }, [position]);

  return (
    <div
      ref={menuRef}
      className="dsf-context-menu"
      style={{ left: adjustedPosition.x, top: adjustedPosition.y }}
    >
      {items.map((item, index) => {
        if (item.separator) {
          return <div key={`sep-${index}`} className="dsf-context-menu__separator" />;
        }

        return (
          <button
            key={item.id}
            className={`dsf-context-menu__item ${item.disabled ? 'dsf-context-menu__item--disabled' : ''} ${item.danger ? 'dsf-context-menu__item--danger' : ''}`}
            onClick={() => {
              if (!item.disabled) {
                onSelect(item.id);
                onClose();
              }
            }}
            disabled={item.disabled}
          >
            {item.icon && <span className="dsf-context-menu__icon">{item.icon}</span>}
            <span className="dsf-context-menu__label">{item.label}</span>
            {item.shortcut && <span className="dsf-context-menu__shortcut">{item.shortcut}</span>}
          </button>
        );
      })}
    </div>
  );
}

// Predefined actions per element type
export type ElementType = 'character' | 'rule' | 'story_segment' | 'world_card' | 'paragraph' | 'location' | 'technology' | 'story_card';

export const ELEMENT_ACTIONS: Record<ElementType, ContextMenuItem[]> = {
  character: [
    { id: 'develop', label: 'Develop character', icon: '◈' },
    { id: 'generate_portrait', label: 'Generate portrait', icon: '◇' },
    { id: 'show_relationships', label: 'Show relationships', icon: '→' },
    { id: 'separator', label: '', separator: true },
    { id: 'ask_agent', label: 'Ask agent about...', icon: '?' },
  ],
  rule: [
    { id: 'test_in_story', label: 'Test in story', icon: '→' },
    { id: 'explore_implications', label: 'Explore implications', icon: '◈' },
    { id: 'check_contradictions', label: 'Check contradictions', icon: '!' },
    { id: 'separator', label: '', separator: true },
    { id: 'ask_agent', label: 'Ask agent about...', icon: '?' },
  ],
  story_segment: [
    { id: 'continue', label: 'Continue from here', icon: '→' },
    { id: 'branch', label: 'Create branch', icon: '◇' },
    { id: 'revise', label: 'Revise segment', icon: '✎' },
    { id: 'generate_illustration', label: 'Generate illustration', icon: '◈' },
    { id: 'separator', label: '', separator: true },
    { id: 'ask_agent', label: 'Ask agent about...', icon: '?' },
  ],
  world_card: [
    { id: 'enter', label: 'Enter world', icon: '→' },
    { id: 'develop', label: 'Develop further', icon: '◈' },
    { id: 'new_story', label: 'Start new story', icon: '+' },
    { id: 'generate_cover', label: 'Generate cover art', icon: '◇' },
  ],
  story_card: [
    { id: 'read', label: 'Read story', icon: '→' },
    { id: 'continue', label: 'Continue story', icon: '◈' },
    { id: 'branch', label: 'Create branch', icon: '◇' },
  ],
  paragraph: [
    { id: 'expand', label: 'Expand this passage', icon: '◈' },
    { id: 'revise', label: 'Revise', icon: '✎' },
    { id: 'what_if', label: 'What if...', icon: '?' },
    { id: 'generate_image', label: 'Illustrate this scene', icon: '◇' },
  ],
  location: [
    { id: 'explore', label: 'Explore location', icon: '→' },
    { id: 'develop', label: 'Add details', icon: '◈' },
    { id: 'generate_image', label: 'Generate image', icon: '◇' },
    { id: 'separator', label: '', separator: true },
    { id: 'ask_agent', label: 'Ask agent about...', icon: '?' },
  ],
  technology: [
    { id: 'explain', label: 'Explain technology', icon: '?' },
    { id: 'explore_implications', label: 'Explore implications', icon: '◈' },
    { id: 'use_in_story', label: 'Use in story', icon: '→' },
  ],
};

export function getActionsForElement(elementType: ElementType): ContextMenuItem[] {
  return ELEMENT_ACTIONS[elementType] || [];
}
