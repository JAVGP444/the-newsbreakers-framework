export default function BrandMark({ size = 44 }: { size?: number }) {
  return (
    <img
      className="brand-logo"
      src="/logo.png"
      alt="The NewsBreakers"
      width={size}
      height={size}
    />
  );
}
