/**
 * 404 Not Found page.
 * Displayed when no matching route is found.
 */
function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-5xl font-bold text-white">404</h1>
      <p className="text-lg text-gray-400">Page not found.</p>
    </div>
  )
}

export default NotFoundPage
