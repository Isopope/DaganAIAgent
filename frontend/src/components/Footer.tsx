export const Footer = () => {
  return (
    <footer className="bg-primary text-white py-6 mt-auto">
      <div className="container mx-auto px-4">
        <div className="text-center space-y-2">
          <p className="text-sm text-white/90">
            © 2025 République Togolaise - Service Public
          </p>
          <p className="text-xs text-white/70">
            Fait par amour par{" "}
            <a 
              href="https://novatekis.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-white transition-colors underline"
            >
              Novatekis
            </a>
            {" "}pour les Togolais
          </p>
          <p className="text-xs text-white/60 italic">
            Le portail intelligent fait par des Togolais pour des Togolais
          </p>
        </div>
      </div>
    </footer>
  );
};
