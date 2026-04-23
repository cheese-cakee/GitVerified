import Link from "next/link";

export default function Footer() {
  return (
    <footer className="w-full bg-black border-t border-white/5 pt-16 pb-8 px-6 md:px-12">
      <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-10 mb-16">
        
        {/* Brand Column */}
        <div className="col-span-2 lg:col-span-2 space-y-4">
          <Link href="/" className="flex items-baseline gap-1 group mb-4">
            <span className="font-serif italic text-2xl text-white font-normal">Candidate</span>
            <span className="font-sans font-bold text-xl text-white tracking-tight">AI</span>
          </Link>
          <h3 className="text-3xl font-bold text-white tracking-tight leading-tight">
             AI-powered candidate verification <br /> that just works.
          </h3>
          <p className="text-gray-500 max-w-sm">
             GitVerified creates a comprehensive profile of a candidate by auditing their codebase, not just their resume PDF.
          </p>
          <div className="pt-4">
             <Link href="/engine" className="inline-flex items-center justify-center px-6 py-2 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-colors">
                 Get Started
             </Link>
          </div>
        </div>

        {/* Links Column 1 */}
        <div className="space-y-4">
           <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Product</h4>
           <ul className="space-y-3 text-sm text-gray-400">
              <li><Link href="#" className="hover:text-white transition-colors">Integration</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Pricing</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Enterprise</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Changelog</Link></li>
           </ul>
        </div>

        {/* Links Column 2 */}
        <div className="space-y-4">
           <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Resources</h4>
           <ul className="space-y-3 text-sm text-gray-400">
              <li><Link href="#" className="hover:text-white transition-colors">Documentation</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">API Reference</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Community</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Blog</Link></li>
           </ul>
        </div>
        
        {/* Links Column 3 */}
        <div className="space-y-4">
           <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Company</h4>
           <ul className="space-y-3 text-sm text-gray-400">
              <li><Link href="#" className="hover:text-white transition-colors">About</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Careers</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Legal</Link></li>
              <li><Link href="#" className="hover:text-white transition-colors">Privacy</Link></li>
           </ul>
        </div>

      </div>

      <div className="max-w-7xl mx-auto pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-gray-600">
         <p>© 2025 GitVerified Inc. All rights reserved.</p>
         <div className="flex gap-6">
            <Link href="#" className="hover:text-gray-400">Privacy Policy</Link>
            <Link href="#" className="hover:text-gray-400">Terms of Service</Link>
         </div>
      </div>
    </footer>
  );
}
