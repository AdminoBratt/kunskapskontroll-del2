import styles from './Button.module.css';

export default function Button({
  children,
  variant = 'primary',
  size,
  loading = false,
  className = '',
  ...props
}) {
  const cls = [
    styles.btn,
    styles[variant],
    size ? styles[size] : '',
    loading ? styles.loading : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button className={cls} disabled={loading || props.disabled} {...props}>
      {loading && <span className={styles.spinner} />}
      {children}
    </button>
  );
}
