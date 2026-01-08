import './canvas.css';
import './globals.css';

export const metadata = {
  title: 'Deep Sci-Fi',
  description: 'Craft immersive science fiction worlds and stories with AI agents',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
