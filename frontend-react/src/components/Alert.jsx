import styles from './Alert.module.css';

export default function Alert({ type = 'info', children }) {
  return <div className={`${styles.alert} ${styles[type]}`}>{children}</div>;
}
