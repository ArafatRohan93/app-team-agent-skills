# Image resource resolver

**Contract:** `lib/core/image_resolver/image_resource.dart`. `ImageResource` has a `path` and `getImageWidget({width, height, boxFit, color})`.

**Implementation:** `lib/shared/image_resolver/`
- `svg_image_resource.dart`: `SVGImageResource` (flutter_svg). `color` is applied as a `srcIn` ColorFilter.
- `png_image_resource.dart`: `PNGImageResource` (`Image.asset`), plus `provider` (an `AssetImage`) for APIs that need an `ImageProvider`.
- `image_resource_resolver.dart`: `ImageResourceResolver`, the registry of every bundled image, as `static const` fields.

## Declaring an image
1. Put the file in `assets/icons/` (small, usually tintable UI icons, named `ic_<name>`) or `assets/images/` (illustrations, logos). Both folders are declared in `pubspec.yaml`.
2. Register it in `ImageResourceResolver`, grouped by folder, named after the file in lowerCamelCase, and add it to `all`:
   ```dart
   abstract final class ImageResourceResolver {
     // --- Icons (assets/icons/) ---
     static const SVGImageResource icWallet = SVGImageResource('$_iconPath/ic_wallet.svg');

     // --- Images (assets/images/) ---
     static const PNGImageResource onboardingHero = PNGImageResource('$_imagePath/onboarding_hero.png');

     static const List<ImageResource> all = [icWallet, onboardingHero];
   }
   ```

## Usage
```dart
ImageResourceResolver.icWallet.getImageWidget(width: AppDimensions.iconMd, color: context.colors.primary)
ImageResourceResolver.onboardingHero.getImageWidget(boxFit: BoxFit.cover)
CircleAvatar(backgroundImage: ImageResourceResolver.avatarPlaceholder.provider)   // PNG only
```
Pass the tint from the theme (`context.colors.*`) so SVG icons follow light and dark mode.

## Testing
`test/shared/image_resolver/image_resource_resolver_test.dart` checks that every entry in `ImageResourceResolver.all` exists on disk and renders. That catches typos and deleted files in CI. Keep `all` in sync.

## Why
- One place lists every asset, so unused or missing files are easy to spot.
- Swapping PNG for SVG, or adding caching or network images, changes one class and no call sites.
- Paths are never typed twice.

## Don'ts
- Never call `Image.asset`, `SvgPicture.asset` or `AssetImage('…')` in `features/`. Always go through `ImageResourceResolver`.
- Don't inline asset path strings anywhere else.
