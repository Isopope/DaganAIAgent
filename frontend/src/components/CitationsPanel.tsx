import { X, ExternalLink } from "lucide-react";
import { Source } from "./SourcesFavicons";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";

interface CitationsPanelProps {
  sources: Source[];
  isOpen: boolean;
  onClose: () => void;
}

export const CitationsPanel = ({ sources, isOpen, onClose }: CitationsPanelProps) => {
  if (!isOpen) return null;

  const getFavicon = (source: Source) => {
    if (source.favicon) return source.favicon;
    try {
      const domain = new URL(source.url).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
      return `https://www.google.com/s2/favicons?domain=example.com&sz=32`;
    }
  };

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return url;
    }
  };

  return (
    <div className="fixed right-0 top-0 h-screen w-[420px] bg-background border-l border-border shadow-2xl animate-slide-in-right z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">Citations</h2>
        <button
          onClick={onClose}
          className="h-8 w-8 rounded-lg hover:bg-accent/10 flex items-center justify-center transition-colors"
        >
          <X className="h-5 w-5 text-muted-foreground" />
        </button>
      </div>

      {/* Sources List */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="space-y-4">
          {sources.map((source, idx) => (
            <a
              key={idx}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-4 rounded-lg border border-border hover:border-accent/60 hover:bg-accent/5 transition-all duration-200 group"
            >
              <div className="flex items-start gap-3">
                <img
                  src={getFavicon(source)}
                  alt=""
                  className="h-5 w-5 rounded-sm mt-0.5 flex-shrink-0"
                  onError={(e) => {
                    e.currentTarget.src = `https://www.google.com/s2/favicons?domain=example.com&sz=32`;
                  }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs text-muted-foreground">
                      {getDomain(source.url)}
                    </span>
                    <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <h3 className="font-semibold text-sm text-foreground mb-1 line-clamp-2 group-hover:text-accent transition-colors">
                    {source.title}
                  </h3>
                  {source.description && (
                    <p className="text-xs text-muted-foreground line-clamp-3 mb-1">
                      {source.description}
                    </p>
                  )}
                  {source.date && (
                    <p className="text-xs text-muted-foreground/70">
                      {source.date}
                    </p>
                  )}
                </div>
              </div>
            </a>
          ))}
        </div>

        {sources.length > 5 && (
          <Button
            variant="outline"
            size="sm"
            className="w-full mt-4"
          >
            More
          </Button>
        )}
      </ScrollArea>
    </div>
  );
};
