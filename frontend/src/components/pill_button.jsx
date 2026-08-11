const SIZE_CLASSES = {
  sm: 'gap-1 px-3 py-1.5 text-xs font-medium',
  md: 'gap-1.5 px-5 py-2.5 text-sm font-semibold',
  lg: 'gap-1.5 px-5 py-3 text-sm font-semibold',
};

export function PillButton({ icon: Icon, iconSize = 13, size = 'md', type = 'button', className = '', children, ...props }) {
  const sizeClasses = SIZE_CLASSES[size] || SIZE_CLASSES.md;
  return (
    <button type={type} className={`inline-flex items-center justify-center rounded-full transition ${sizeClasses} ${className}`} {...props}>
      {Icon && <Icon size={iconSize} />}
      {children}
    </button>
  );
}
