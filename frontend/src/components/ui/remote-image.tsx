type RemoteImageProps = {
  src: string;
  alt: string;
  className?: string;
};

export function RemoteImage({ src, alt, className = "" }: RemoteImageProps) {
  return (
    <span
      role="img"
      aria-label={alt}
      className={`block bg-cover bg-center bg-no-repeat ${className}`}
      style={{ backgroundImage: `url(${JSON.stringify(src)})` }}
    />
  );
}
