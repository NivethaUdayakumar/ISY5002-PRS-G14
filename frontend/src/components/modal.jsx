import { X } from 'lucide-react';

const DEFAULT_CLOSE_CLASSNAME =
  'rounded-full bg-gray-100 p-2 text-gray-600 transition hover:bg-gray-200 hover:text-gray-900';

export function CloseButton({ onClick, label = 'Close modal', className = DEFAULT_CLOSE_CLASSNAME, size = 16 }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} className={className}>
      <X size={size} />
    </button>
  );
}

export function ModalOverlay({ align = 'center', className = '', style, children }) {
  const alignClass = align === 'end' ? 'items-end sm:items-center' : 'items-center';
  return (
    <div className={`fixed inset-0 z-50 flex ${alignClass} justify-center bg-black/50 px-4 ${className}`} style={style}>
      {children}
    </div>
  );
}

export function ModalCard({ className = '', children }) {
  return <div className={`flex w-full flex-col overflow-hidden bg-white ${className}`}>{children}</div>;
}

export function ModalHeader({ onClose, closeLabel = 'Close modal', closeClassName, borderClassName = 'border-gray-200', className = 'px-6 py-5', children }) {
  return (
    <div className={`flex flex-shrink-0 items-center justify-between border-b ${borderClassName} ${className}`}>
      {children}
      <CloseButton onClick={onClose} label={closeLabel} className={closeClassName} />
    </div>
  );
}
