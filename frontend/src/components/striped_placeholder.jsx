export function StripedPlaceholder({ className = '', style, children }) {
  return (
    <div
      className={`relative overflow-hidden ${className}`}
      style={{
        backgroundImage:
          'repeating-linear-gradient(135deg, rgba(0,0,0,0.06) 0px, rgba(0,0,0,0.06) 2px, transparent 2px, transparent 8px)',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
