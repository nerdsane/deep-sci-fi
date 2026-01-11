/**
 * InteractiveElement - Makes any element contextually interactive
 *
 * Wraps elements to provide:
 * - Right-click context menu
 * - Hover highlight
 * - Click-to-interact behavior
 * - Keyboard accessibility
 */
import React, { useState, useCallback, type ReactNode, type MouseEvent, type KeyboardEvent } from 'react';
import { ContextMenu, getActionsForElement, type ElementType, type ContextMenuItem } from './ContextMenu';

export interface InteractiveElementProps {
  elementType: ElementType;
  elementId: string;
  elementData?: any;
  children: ReactNode;
  onAction: (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => void;
  customActions?: ContextMenuItem[];
  disabled?: boolean;
  className?: string;
}

export function InteractiveElement({
  elementType,
  elementId,
  elementData,
  children,
  onAction,
  customActions,
  disabled = false,
  className = '',
}: InteractiveElementProps) {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [isHovered, setIsHovered] = useState(false);

  const handleContextMenu = useCallback((e: MouseEvent) => {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }, [disabled]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (disabled) return;
    // Open context menu on Shift+F10 or context menu key
    if (e.key === 'ContextMenu' || (e.shiftKey && e.key === 'F10')) {
      e.preventDefault();
      const rect = (e.target as HTMLElement).getBoundingClientRect();
      setContextMenu({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });
    }
  }, [disabled]);

  const handleCloseMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleSelectAction = useCallback((actionId: string) => {
    onAction(actionId, elementId, elementType, elementData);
    setContextMenu(null);
  }, [onAction, elementId, elementType, elementData]);

  const actions = customActions || getActionsForElement(elementType);

  return (
    <>
      <div
        className={`dsf-interactive-element ${isHovered ? 'dsf-interactive-element--hovered' : ''} ${disabled ? 'dsf-interactive-element--disabled' : ''} ${className}`}
        onContextMenu={handleContextMenu}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onKeyDown={handleKeyDown}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-haspopup="menu"
        aria-expanded={contextMenu !== null}
        data-element-type={elementType}
        data-element-id={elementId}
      >
        {children}
      </div>

      {contextMenu && (
        <ContextMenu
          items={actions}
          position={contextMenu}
          onSelect={handleSelectAction}
          onClose={handleCloseMenu}
        />
      )}
    </>
  );
}
