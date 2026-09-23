import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// One motion spec for every route: fade + subtle horizontal slide.
abstract final class AppPageTransition {
  static const duration = Duration(milliseconds: 300);
  static const curve = Curves.easeInOutCubicEmphasized;
  static const _slideFraction = 0.06;

  static Widget transitionsBuilder(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    final incoming = CurvedAnimation(parent: animation, curve: curve);
    final outgoing = CurvedAnimation(parent: secondaryAnimation, curve: curve);

    return SlideTransition(
      position: Tween<Offset>(
        begin: Offset.zero,
        end: const Offset(-_slideFraction, 0),
      ).animate(outgoing),
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(_slideFraction, 0),
          end: Offset.zero,
        ).animate(incoming),
        child: FadeTransition(opacity: incoming, child: child),
      ),
    );
  }
}

/// Every `GoRoute.pageBuilder` funnels through this so transitions are
/// defined in one place.
CustomTransitionPage<T> buildTransitionPage<T>({
  required GoRouterState state,
  required Widget child,
}) => CustomTransitionPage<T>(
  key: state.pageKey,
  name: state.name,
  child: child,
  transitionDuration: AppPageTransition.duration,
  reverseTransitionDuration: AppPageTransition.duration,
  transitionsBuilder: AppPageTransition.transitionsBuilder,
);
