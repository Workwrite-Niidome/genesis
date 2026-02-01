import WorldCanvas from '../world/WorldCanvas';
import MobileAISheet from './MobileAISheet';

export default function MobileWorldView() {
  return (
    <div className="relative w-full h-full">
      {/* Full-screen 3D canvas with touch support */}
      <WorldCanvas showGenesis={false} />

      {/* AI detail bottom sheet */}
      <MobileAISheet />
    </div>
  );
}
